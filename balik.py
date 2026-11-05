"""Su kolonu hedefleri: balik, gaz kabarcigi, parazit + goreli bulaniklik.

Yontem:
  1) Her uzaklik kutusu icin "bos su" referansi (medyan) ve ping basina kazanc ofseti cikarilir.
  2) Esigi asan hucreler (ping x derinlik) bitisiklik ile hedeflere (izlere) gruplanir.
  3) Her iz siniflanir:
       parazit  : 1-2 ping suren, dikey uzun cizgi
       kabarcik : dibe yakin baslayip zamanla surekli yukselen iz (>= 30 cm)
       balik    : dibe degmeyen, en az 3 ping suren, dikeyde dar iz (DownVu'de yay/egik cizgi)
       belirsiz : digerleri
  4) Bulaniklik: hedefler disindaki su kolonunun referansa gore ortalama fazlasi (goreli).
Sinirlar: verici cinlamasi nedeniyle yuzeyin ilk ~1,4 m'si olculemez; boy / tur bilgisi cikmaz
(cihaz kalibre degil); DownVu genis yan aciyla gordugu icin yan taraftaki balik da sayilir.

Kullanim:  .venv\\Scripts\\python balik.py   (once sukolonu_onbellek.py ve zemin.py)
"""
import math
import os
from collections import deque
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from uydu_altlik import Mozaik, merc, altlik

OUT = "cozumleme/balik"
os.makedirs(OUT, exist_ok=True)
RINGDOWN = 1.40
DIP_PAYI = 0.15
PING_HZ = 26.0


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
b_ham = np.load("cozumleme/zemin/_ping_oznitelik_onbellek.npz")["bottom"]
# dip secimi yer yer 30-70 cm fazla derin kayiyor; su kolonu icin guvenli taraf: ~2 sn icindeki en sig okuma
b = pd.Series(b_ham).rolling(51, center=True, min_periods=5).quantile(0.05).to_numpy()
z = np.load("cozumleme/sukolonu/_sukolonu_onbellek.npz")
W = z["wc"].astype(np.float32)
DZ = float(z["dz"])
nb = W.shape[1]
zc = (np.arange(nb) + 0.5) * DZ
hiz = d["speed_ms"].where(d["speed_ms"] < 5).rolling(51, center=True, min_periods=5).median().to_numpy()

valid = (zc[None, :] >= RINGDOWN) & (zc[None, :] <= (b[:, None] - DIP_PAYI)) & np.isfinite(b)[:, None]
# 1) referans ve ofset
Wv = np.where(valid, W, np.nan)
R = np.nanmedian(Wv, 0)
X = W - R[None, :]
off = np.nanmedian(np.where(valid, X, np.nan), 1)
X = X - np.nan_to_num(off)[:, None]
ref = X[valid]
mad = 1.4826 * np.median(np.abs(ref - np.median(ref)))
T = np.median(ref) + 4 * mad
M = valid & (X > T)
print(f"Esik {T:.0f} (robust sd {mad:.0f}); gecerli hucre {valid.sum():,}, esik ustu {M.sum():,}")

# tum kolonu kesen parazit ping'leri
frac = M.sum(1) / np.maximum(valid.sum(1), 1)
parazit_ping = frac > 0.5

# 2) bitisik bilesenler (8-komsuluk)
lab = -np.ones(M.shape, np.int32)
izler = []
pp, zz = np.nonzero(M)
for p0, z0 in zip(pp, zz):
    if lab[p0, z0] >= 0:
        continue
    q = deque([(p0, z0)]); lab[p0, z0] = len(izler); cells = []
    while q:
        p, k_ = q.popleft(); cells.append((p, k_))
        for dp in (-1, 0, 1):
            for dk in (-1, 0, 1):
                a_, c_ = p + dp, k_ + dk
                if 0 <= a_ < M.shape[0] and 0 <= c_ < nb and M[a_, c_] and lab[a_, c_] < 0:
                    lab[a_, c_] = len(izler); q.append((a_, c_))
    izler.append(np.array(cells))

rows = []
for i, c in enumerate(izler):
    p, k_ = c[:, 0], c[:, 1]
    pings = np.unique(p)
    zmean = np.array([zc[k_[p == q]].mean() for q in pings])
    dur = pings[-1] - pings[0] + 1
    ext = (k_.max() - k_.min() + 1) * DZ
    dipe = (zc[k_.max()] >= b[pings].min() - DIP_PAYI - 0.10)
    # yukselme: ilk ve son ceyrekteki ortalama derinlik farki (pozitif = yukseliyor)
    q4 = max(1, len(pings) // 4)
    yuk = zmean[:q4].mean() - zmean[-q4:].mean()
    ilk_dipte = zmean[:q4].max() >= b[pings[:q4]].min() - DIP_PAYI - 0.15
    # balik izi DownVu'de yay: once yaklasir (derinlik azalir) sonra uzaklasir; kabarcik tek yonlu yukselir
    tepe = zmean.argmin()
    yay = 0 < tepe < len(zmean) - 1 and (zmean[0] - zmean[tepe] > 0.03) and (zmean[-1] - zmean[tepe] > 0.03)
    if dur <= 2 and ext >= 0.30:
        tur = "parazit"
    elif np.all(parazit_ping[pings]):
        tur = "parazit"
    elif ilk_dipte and yuk >= 0.30 and not yay and dur >= 5:
        tur = "kabarcik"
    elif dur >= 3 and not dipe and ext <= 0.5:
        tur = "balik"
    else:
        tur = "belirsiz"
    pm = pings[len(pings) // 2]
    rows.append(dict(iz=i, tur=tur, ping=pm, sure_ping=dur, dikey_m=ext, derinlik=zmean.mean(), yukselme=yuk,
                     yay=yay, guc=X[p, k_].max(), lat=d["lat"].iat[pm], lon=d["lon"].iat[pm],
                     time_s=d["time_s"].iat[pm], hiz=hiz[pm], dip=b[pm],
                     p_ilk=pings[0], p_son=pings[-1], z_ilk=zmean[0], z_son=zmean[-1]))
Hc = pd.DataFrame(rows)
# cok kisa ve kucuk lekeler (1-2 hucre) -> gurultu, analiz disi
Hc = Hc[~((Hc["sure_ping"] <= 2) & (Hc["dikey_m"] < 0.30))].reset_index(drop=True)

# ayni izin kopuk parcalarini birlestir: bir parca digerinin bittigi yerden <= 40 ping sonra ve
# <= 30 cm derinlik farkiyla basliyorsa ayni hedef
Hc = Hc.sort_values("p_ilk").reset_index(drop=True)
Hc["grup"] = -1
acik = []          # (grup, p_son, z_son)
gno = 0
for i, r in Hc.iterrows():
    if r["tur"] == "parazit":
        Hc.at[i, "grup"] = gno; gno += 1
        continue
    hedef = None
    for j, (g_, ps, zs) in enumerate(acik):
        if 0 <= r["p_ilk"] - ps <= 40 and abs(r["z_ilk"] - zs) <= 0.30:
            hedef = j
            break
    if hedef is None:
        acik.append((gno, r["p_son"], r["z_son"])); Hc.at[i, "grup"] = gno; gno += 1
    else:
        g_ = acik[hedef][0]
        acik[hedef] = (g_, max(acik[hedef][1], r["p_son"]), r["z_son"]); Hc.at[i, "grup"] = g_
    acik = [a for a in acik if r["p_ilk"] - a[1] <= 40]


def grup_ozet(s):
    en = s.loc[s["guc"].idxmax()]
    tur = ("balik" if (s["tur"] == "balik").any() else
           "kabarcik" if (s["tur"] == "kabarcik").any() else s["tur"].iloc[0])
    return pd.Series(dict(tur=tur, parca=len(s), ping=int(en["ping"]), sure_ping=s["p_son"].max() - s["p_ilk"].min() + 1,
                          derinlik=s["derinlik"].mean(), z_min=s[["z_ilk", "z_son"]].min().min(),
                          guc=s["guc"].max(), lat=en["lat"], lon=en["lon"], time_s=en["time_s"], hiz=en["hiz"],
                          dip=en["dip"]))


H = Hc.groupby("grup").apply(grup_ozet, include_groups=False).reset_index()
Hc["grup_tur"] = Hc["grup"].map(H.set_index("grup")["tur"])
print("Parca:", len(Hc), " -> birlesik iz:", len(H))
print(H["tur"].value_counts().to_string())
H.to_csv(os.path.join(OUT, "su_kolonu_hedefleri.csv"), index=False)

# ayni balik tekne yavasken uzun sure izlenebilir: sayimi tekne ilerlerken (>= 0,5 km/sa) yap
Hs = H[H["hiz"] >= 0.5 / 3.6]
seyir_s = (np.nan_to_num(hiz) >= 0.5 / 3.6).sum() / PING_HZ
yol_m = np.nansum(np.where(np.nan_to_num(hiz) >= 0.5 / 3.6, hiz, 0)) / PING_HZ
nf = (Hs["tur"] == "balik").sum()
nk = (Hs["tur"] == "kabarcik").sum()
print(f"Seyir: {seyir_s / 60:.1f} dk, {yol_m:.0f} m yol -> balik izi {nf} ({nf / yol_m * 100:.1f} / 100 m), kabarcik {nk}")

# 4) bulaniklik (hedefsiz su kolonu fazlasi, ping basina)
Xc = np.where(valid & ~M & ~parazit_ping[:, None], X + np.nan_to_num(off)[:, None], np.nan)
bul = np.nanmedian(Xc, 1)

# ------------------------------------------------------------------ gorseller
moz = Mozaik()
k = 1 / math.cos(math.radians(d["lat"].mean()))
rmx, rmy = merc(d["lat"].to_numpy(), d["lon"].to_numpy())
VIEW = [rmx.min() - 25 * k, rmx.max() + 25 * k, rmy.min() - 25 * k, rmy.max() + 25 * k]

# B: harita (balik yogunlugu + kabarcik + bulaniklik)
x0, y0 = d["e"].min(), d["n"].min()
G = 10.0
d["gx"], d["gy"] = ((d["e"] - x0) // G).astype(int), ((d["n"] - y0) // G).astype(int)
d["seyir"] = np.nan_to_num(hiz) >= 0.5 / 3.6
d["yol"] = np.where(d["seyir"], np.nan_to_num(hiz), 0) / PING_HZ
d["bul"] = np.where(d["seyir"], bul, np.nan)
Hs = Hs.merge(d[["gx", "gy"]], left_on="ping", right_index=True)
cell = d.groupby(["gx", "gy"]).agg(yol=("yol", "sum"), lat=("lat", "mean"), lon=("lon", "mean"), bul=("bul", "median"))
cell["balik"] = Hs[Hs["tur"] == "balik"].groupby(["gx", "gy"]).size()
cell["balik"] = cell["balik"].fillna(0)
cell = cell[cell["yol"] >= 15]
cell["yog"] = cell["balik"] / cell["yol"] * 100
cmx, cmy = merc(cell["lat"], cell["lon"])

fig, axs = plt.subplots(1, 2, figsize=(18, 10))
altlik(axs[0], moz, VIEW, k, f"Balik izi yogunlugu (10 m hucre; iz / 100 m seyir) ve gaz kabarciklari\n"
       f"toplam {nf} balik izi, {nk} kabarcik izi (tekne >= 0,5 km/sa)")
sc = axs[0].scatter(cmx, cmy, c=cell["yog"], s=430, marker="s", cmap="YlOrRd", alpha=0.75,
                    vmin=0, vmax=np.nanpercentile(cell["yog"], 95))
plt.colorbar(sc, ax=axs[0], shrink=0.55, label="balik izi / 100 m")
fb = Hs[Hs["tur"] == "balik"]
fmx, fmy = merc(fb["lat"], fb["lon"])
axs[0].scatter(fmx, fmy, s=6, c="black", alpha=0.6, label="balik izi")
kb = Hs[Hs["tur"] == "kabarcik"]
kmx, kmy = merc(kb["lat"], kb["lon"])
axs[0].scatter(kmx, kmy, s=60, marker="^", c="cyan", edgecolors="k", label="gaz kabarcigi izi")
axs[0].legend(loc="upper left", fontsize=9)
# Bulaniklik olcusu kontrol edildi: cihazin otomatik kazanciyla (r~-0,64) ve tekne hiziyla (r~+0,53)
# guclu iliskili -> sudaki bulanikligi degil kazanc / govde alti gurultusunu gosteriyor. Harita cizilmiyor.
s_ = pd.DataFrame({"bul": bul, "gain": d["gain"], "hiz": hiz}).dropna()
r_g, r_h = s_.corr().loc["bul", "gain"], s_.corr().loc["bul", "hiz"]
axs[1].axis("off")
axs[1].text(0.5, 0.5, "Bulaniklik haritasi cizilmedi\n\n"
            f"Su kolonu yanki seviyesi cihazin otomatik kazanciyla (r = {r_g:.2f})\n"
            f"ve tekne hiziyla (r = {r_h:.2f}) birlikte degisiyor.\n"
            "Yani sudaki bulanikligi degil, cihaz ayarini ve\n"
            "hizla artan govde alti gurultusunu olcuyor.",
            ha="center", va="center", fontsize=12, transform=axs[1].transAxes,
            bbox=dict(boxstyle="round", fc="#f6f2e8", ec="#c9b98a"))
kaydet(fig, "F1_balik_kabarcik_bulaniklik.png")

# F2: derinlik dagilimi + zaman icinde
fig, axs = plt.subplots(1, 3, figsize=(16, 4.5))
for t_, c_ in [("balik", "tab:orange"), ("kabarcik", "tab:cyan"), ("belirsiz", "grey")]:
    s = Hs[Hs["tur"] == t_]
    if len(s):
        axs[0].hist(s["derinlik"], bins=np.arange(1.4, 3.3, 0.1), alpha=0.6, color=c_, label=f"{t_} ({len(s)})",
                    orientation="horizontal")
axs[0].invert_yaxis(); axs[0].set_ylabel("derinlik (m)"); axs[0].set_xlabel("iz sayisi"); axs[0].legend()
axs[0].set_title("Hedeflerin derinlik dagilimi (1,4 m ustu olculemez)")
s = Hs[Hs["tur"] == "balik"]
axs[1].hist(s["derinlik"] / s["dip"], bins=np.linspace(0.4, 1, 13), color="tab:orange")
axs[1].set_xlabel("derinlik / dip derinligi (1 = dip)"); axs[1].set_title("Baliklar dibe ne kadar yakin")
tb = pd.cut(d["time_s"] / 60, np.arange(5, 60, 5))
yol_t = d.groupby(tb, observed=True)["yol"].sum()
bal_t = s.groupby(pd.cut(s["time_s"] / 60, np.arange(5, 60, 5)), observed=True).size()
axs[2].bar([str(i.left) for i in yol_t.index], (bal_t.reindex(yol_t.index).fillna(0) / yol_t * 100).values, color="tab:orange")
axs[2].set_xlabel("kayit dakikasi"); axs[2].set_ylabel("balik izi / 100 m"); axs[2].set_title("Zamana gore")
kaydet(fig, "F2_derinlik_ve_zaman.png")

# F3: ornek kesitler - tespitler isaretli
lo, hi = np.percentile(W[::40], [5, 99.7])
ornek = []
for t_ in ["balik", "kabarcik", "belirsiz"]:
    s = Hs[Hs["tur"] == t_].sort_values("guc", ascending=False)
    ornek += [(t_, int(p)) for p in s["ping"].head(2)]
fig, axs = plt.subplots(len(ornek), 1, figsize=(13, 2.3 * len(ornek)))
axs = np.atleast_1d(axs)
renk = {"balik": "orange", "kabarcik": "cyan", "belirsiz": "white", "parazit": "red"}
for ax, (t_, p0) in zip(axs, ornek):
    sl = slice(max(0, p0 - 200), min(len(d), p0 + 200))
    ax.imshow(W[sl].T, aspect="auto", cmap="copper", vmin=lo, vmax=hi, extent=[sl.start, sl.stop, nb * DZ, 0])
    ax.plot(np.arange(sl.start, sl.stop), b[sl], color="cyan", lw=0.4)
    ax.axhline(RINGDOWN, color="red", lw=0.5, ls=":")
    for r in Hc[(Hc["p_son"] >= sl.start) & (Hc["p_ilk"] < sl.stop)].itertuples():
        c = izler[r.iz]
        ax.scatter(c[:, 0], zc[c[:, 1]], s=0.6, c=renk[r.grup_tur], alpha=0.5)
    ax.set_ylim(min(3.4, np.nanmax(b[sl]) + 0.4), 0.8)
    ax.set_title(f"Ornek: {t_}  ({d['time_s'].iat[p0] / 60:.1f}. dk)", fontsize=10, loc="left")
    ax.set_ylabel("m"); ax.set_xticks([])
fig.suptitle("Tespit edilen izler (turuncu: balik, camgobegi: kabarcik, beyaz: belirsiz, kirmizi: parazit; "
             "kirmizi noktali cizgi: olcum siniri 1,4 m)", fontsize=10)
kaydet(fig, "F3_ornek_kesitler.png")
