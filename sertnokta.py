"""Sert nokta / nesne taramasi (yumusatma YOK, ping ping).

Iki tur aday aranir:
  A) SERT YAMA: cevresindeki ayni derinlikteki dibe gore guclu dip yankisi + dusuk penetrasyon
     + hizli sonum + guclu ikinci yanki (2 x derinlik) birlikte ve ardisik ping'lerde.
  B) TUMSEK: dip cizgisinin cevresinden belirgin yukari cikmasi (kaya, batik nesne, yigin).
Tekne yavasken (< 1 km/sa) olcumler disarida (pervane bulanmasi, ayni noktanin tekrar tekrar olculmesi).

Cikti (cozumleme/sertnokta): S1 harita, S2 aday kesitleri, sert_nokta_adaylari.csv / .gpx
Kullanim:  .venv\\Scripts\\python sertnokta.py
"""
import math
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from uydu_altlik import Mozaik, merc, altlik

OUT = "cozumleme/sertnokta"
os.makedirs(OUT, exist_ok=True)
SUREK = 9              # ardisik ping (~0,35 sn)
ESIK_SERT = 3.0        # birlesik sertlik skoru esigi (robust z)
ESIK_TUMSEK = 0.15     # dip cizgisinin cevreden yukselmesi (m)
GRUP_MESAFE = 3.0      # bu mesafedeki adaylar tek nokta sayilir (m)


def kaydet(fig, ad, dpi=130):
    yol = os.path.join(OUT, ad)
    if os.path.exists(yol):
        os.remove(yol)
    fig.tight_layout()
    fig.savefig(yol, dpi=dpi)
    plt.close(fig)
    print("->", yol)


d = pd.read_csv("cozumleme/meta/B001_ds_hifreq_meta.csv")
has = d["inst_dep_m"].notna()
seg = (has.astype(int).diff() != 0).cumsum()
d = d[has & (has.groupby(seg).transform("sum") >= 1000)].reset_index(drop=True)
z = np.load("cozumleme/zemin/_ping_oznitelik_onbellek.npz")
for kk in ["bottom", "noise", "peak", "tail", "decay", "e2", "rise"]:
    d[kk] = z[kk].astype(float)
for kk in ["peak", "tail", "e2"]:
    d[kk] = d[kk] + d["noise"]                     # mutlak
d["contrast"] = d["tail"] - d["peak"]
hiz = d["speed_ms"].where(d["speed_ms"] < 5).rolling(51, center=True, min_periods=5).median()
d["gecerli"] = d["bottom"].notna() & (hiz >= 1.0 / 3.6)

# derinlik bandina gore robust z (ayni derinlikteki tipik dibe gore)
d["band"] = (d["bottom"] / 0.1).round()
v = d[d["gecerli"]]


def rz(col):
    g = v.groupby("band")[col]
    med = g.transform("median")
    mad = g.transform(lambda s: 1.4826 * np.median(np.abs(s - s.median())))
    out = pd.Series(np.nan, index=d.index)
    out[v.index] = (v[col] - med) / mad.replace(0, np.nan)
    return out


d["z_peak"], d["z_con"], d["z_dec"], d["z_e2"] = rz("peak"), rz("contrast"), rz("decay"), rz("e2")
d["sertlik"] = (d["z_peak"] - d["z_con"] + d["z_dec"] + d["z_e2"].fillna(0)) / np.where(d["z_e2"].notna(), 2.0, math.sqrt(3))
d["sertlik_s"] = d["sertlik"].rolling(SUREK, center=True, min_periods=SUREK // 2 + 1).mean()
d["yukselme"] = -(d["bottom"] - d["bottom"].rolling(151, center=True, min_periods=30).median())
d["yukselme_s"] = d["yukselme"].rolling(SUREK, center=True, min_periods=SUREK // 2 + 1).median()

# dip okumasinin kararsiz oldugu yerlerde "tumsek" sahte cikar (okuma gurultusu): 2 sn icinde dip
# secimi 5 cm'den fazla oynuyorsa tumsek sayma
d["dip_oynak"] = d["bottom"].diff().abs().rolling(51, center=True, min_periods=10).median() > 0.05
d.loc[d["dip_oynak"], "yukselme_s"] = np.nan
aday = d[d["gecerli"] & ((d["sertlik_s"] > ESIK_SERT) | (d["yukselme_s"] > ESIK_TUMSEK))].copy()
print(f"Gecerli ping {d['gecerli'].sum()}, esigi gecen ping {len(aday)}")

# yere gore grupla
x0, y0 = d["e"].min(), d["n"].min()
aday["x"], aday["y"] = aday["e"] - x0, aday["n"] - y0
grup = -np.ones(len(aday), int)
P = aday[["x", "y"]].to_numpy()
gid = 0
for i in range(len(aday)):
    if grup[i] >= 0:
        continue
    st = [i]; grup[i] = gid
    while st:
        j = st.pop()
        nb = np.where((grup < 0) & (np.hypot(P[:, 0] - P[j, 0], P[:, 1] - P[j, 1]) < GRUP_MESAFE))[0]
        grup[nb] = gid
        st.extend(nb.tolist())
    gid += 1
aday["grup"] = grup
G = aday.groupby("grup").agg(
    ping=("sertlik", "size"), lat=("lat", "mean"), lon=("lon", "mean"), x=("x", "mean"), y=("y", "mean"),
    derinlik=("bottom", "median"), sertlik=("sertlik_s", "max"), yukselme_m=("yukselme_s", "max"),
    gecis=("time_s", lambda s: (np.diff(np.sort(s.to_numpy())) > 20).sum() + 1),
    t_ilk=("time_s", "min"), idx=("sertlik_s", "idxmax"))
G = G[G["ping"] >= SUREK].copy()
G["tur"] = np.where(G["yukselme_m"] > ESIK_TUMSEK, "Tumsek / nesne", "Sert yama")
G.loc[(G["yukselme_m"] > ESIK_TUMSEK) & (G["sertlik"] > ESIK_SERT), "tur"] = "Sert tumsek (kaya / nesne olasi)"
# guven: birden fazla gecisle tekrar gorulduyse yuksek
G["guven"] = np.where(G["gecis"] >= 2, "yuksek (tekrar goruldu)", "orta (tek gecis)")
G = G.sort_values(["gecis", "ping"], ascending=False).reset_index(drop=True)
G["no"] = [f"N{i + 1:02d}" for i in range(len(G))]
print(G[["no", "tur", "ping", "gecis", "derinlik", "sertlik", "yukselme_m", "lat", "lon"]].round(3).to_string(index=False))
G.drop(columns=["idx"]).round(6).to_csv(os.path.join(OUT, "sert_nokta_adaylari.csv"), index=False, encoding="utf-8-sig")
wpt = "\n".join(f'  <wpt lat="{r.lat:.7f}" lon="{r.lon:.7f}"><name>{r.no}</name><desc>{r.tur}, {r.derinlik:.1f} m</desc></wpt>'
                for r in G.itertuples())
with open(os.path.join(OUT, "sert_nokta_adaylari.gpx"), "w", encoding="utf-8") as f:
    f.write('<?xml version="1.0" encoding="UTF-8"?>\n<gpx version="1.1" creator="sertnokta.py" '
            f'xmlns="http://www.topografix.com/GPX/1/1">\n{wpt}\n</gpx>\n')

# ------------------------------------------------------------------ S1 harita
moz = Mozaik()
k = 1 / math.cos(math.radians(d["lat"].mean()))
rmx, rmy = merc(d["lat"].to_numpy(), d["lon"].to_numpy())
VIEW = [rmx.min() - 25 * k, rmx.max() + 25 * k, rmy.min() - 25 * k, rmy.max() + 25 * k]
fig, ax = plt.subplots(figsize=(10, 11))
altlik(ax, moz, VIEW, k, f"Sert nokta / nesne adaylari ({len(G)} aday; yumusatmasiz, tekne >= 1 km/sa)")
sc = ax.scatter(rmx[::3], rmy[::3], c=d["sertlik_s"].to_numpy()[::3], cmap="RdYlBu_r", vmin=-3, vmax=3, s=1.5, alpha=0.8)
plt.colorbar(sc, ax=ax, shrink=0.55, label="birlesik sertlik skoru (ayni derinlikteki dibe gore, z)")
renk = {"Sert yama": "red", "Tumsek / nesne": "magenta", "Sert tumsek (kaya / nesne olasi)": "black"}
gmx, gmy = merc(G["lat"], G["lon"])
for (r, mx_, my_) in zip(G.itertuples(), gmx, gmy):
    ax.plot(mx_, my_, marker="o", ms=13, mfc="none", mec=renk[r.tur], mew=2.2)
    ax.annotate(r.no, (mx_, my_), xytext=(8, 6), textcoords="offset points", fontsize=9, weight="bold",
                bbox=dict(boxstyle="round,pad=0.15", fc="white", alpha=0.85))
for t, c in renk.items():
    ax.plot([], [], "o", mfc="none", mec=c, mew=2, ms=10, label=t)
ax.legend(loc="upper left", fontsize=9)
kaydet(fig, "S1_sert_nokta_haritasi.png")

# ------------------------------------------------------------------ S2 aday kesitleri (tam su kolonu + ikinci yanki bolgesi)
wc = np.load("cozumleme/sukolonu/_sukolonu_onbellek.npz")
W, DZ = wc["wc"], float(wc["dz"])
ust = G.head(6)
if len(ust):
    fig, axs = plt.subplots(len(ust), 1, figsize=(13, 2.6 * len(ust)))
    axs = np.atleast_1d(axs)
    lo, hi = np.percentile(W[::50], [5, 99.7])
    for ax, r in zip(axs, ust.itertuples()):
        i0 = int(r.idx)
        sl = slice(max(0, i0 - 260), min(len(d), i0 + 260))
        ax.imshow(W[sl].T, aspect="auto", cmap="copper", vmin=lo, vmax=hi,
                  extent=[sl.start - i0, sl.stop - i0, W.shape[1] * DZ, 0])
        ax.plot(np.arange(sl.start, sl.stop) - i0, d["bottom"].to_numpy()[sl], color="cyan", lw=0.5)
        ax.plot(np.arange(sl.start, sl.stop) - i0, 2 * d["bottom"].to_numpy()[sl], color="cyan", lw=0.5, ls="--")
        ax.axvline(0, color="red", lw=0.8)
        ax.set_ylabel("derinlik (m)")
        ax.set_title(f"{r.no}: {r.tur} - derinlik {r.derinlik:.2f} m, {r.gecis} gecis, {r.ping} ping, "
                     f"{r.t_ilk / 60:.1f}. dk", fontsize=10, loc="left")
    axs[-1].set_xlabel("ping (0 = adayin en guclu ani; ~26 ping/sn)   cizgi: dip, kesikli: 2 x derinlik (ikinci yanki)")
    kaydet(fig, "S2_aday_kesitleri.png")
