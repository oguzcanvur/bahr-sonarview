"""Dip ustu yankilardan su bitkisi (makrofit) ortusu tahmini.

Fikir: Su kolonundaki "bos su" yankisi vericiden uzakliga bagli bir egri izler (R).
Dibin hemen ustunde bu egrinin belirgin ustune cikan ve dipten yukari kesintisiz
uzanan yanki -> dipte duran bir yapi (bitki ortusu, ya da akiskan camur tabakasi).
Tek tek ve dipten kopuk yankilar (balik) kesintisizlik sartiyla elenir.

Sinirlar:
  - Verici cinlamasi ~1.35 m'ye kadar suruyor: daha sig yerlerde olcum yapilamaz.
  - 5-10 cm'den alcak, dibe yatik ortu ile akiskan camur tabakasi ayirt edilemez.
  - Kasim ayi kaydi: yaz bitki ortusunu temsil etmeyebilir.

Kullanim:  .venv\\Scripts\\python bitki.py     (once zemin.py calismis olmali: onbellegi kullanir)
"""
import math
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.tri as mtri

META = "cozumleme/meta/B001_ds_hifreq_meta.csv"
CACHE = "cozumleme/zemin/_ping_oznitelik_onbellek.npz"
OUT = "cozumleme/bitki"
ZREL = np.arange(-0.8, 2.5, 0.01)       # zemin.py ile ayni eksen
RINGDOWN = 1.35                          # vericiden bu uzakliga kadar olcum guvenilmez (m)
PENCERE = (-0.50, -0.08)                 # tabana gore incelenen pencere (m); -0.08..0 dip secim izi
MIN_PENCERE = 0.20                       # gecerli sayilmak icin en az bu kadar temiz pencere (m)
CELL, SIGMA, MAX_EDGE = 1.0, 4.0, 7.0
os.makedirs(OUT, exist_ok=True)


def kaydet(fig, ad, dpi=130):
    yol = os.path.join(OUT, ad)
    if os.path.exists(yol):
        os.remove(yol)
    fig.tight_layout()
    fig.savefig(yol, dpi=dpi)
    plt.close(fig)
    print("->", yol)


# ------------------------------------------------------------------ veri (zemin.py ile ayni ping sirasi)
d = pd.read_csv(META)
has = d["inst_dep_m"].notna()
seg = (has.astype(int).diff() != 0).cumsum()
d = d[has & (has.groupby(seg).transform("sum") >= 1000)].reset_index(drop=True)
z = np.load(CACHE)
b, noise = z["bottom"], z["noise"]
prof = z["prof"] + noise[:, None]          # mutlak yanki degeri
assert len(d) == len(b), "onbellek ile metadata uyusmuyor; zemin.py'yi yeniden calistirin"
ok = np.isfinite(b)

# ------------------------------------------------------------------ 1) bos su referansi R(vericiden uzaklik)
zabs = b[:, None] + ZREL[None, :]
clean = (ZREL[None, :] <= -0.40) & ok[:, None]            # tabandan en az 40 cm yukari = bos su varsayimi
edges = np.arange(0.2, 3.0, 0.02)
idx = np.digitize(zabs, edges)
Rv = np.full(edges.size + 1, np.nan)
for i in range(1, edges.size):
    v = prof[clean & (idx == i)]
    if v.size > 200:
        Rv[i] = np.nanmedian(v)
Rc = 0.5 * (edges[:-1] + edges[1:])
Rcurve = Rv[1:edges.size]
good = np.isfinite(Rcurve)
R = np.interp(zabs, Rc[good], Rcurve[good], left=np.nan, right=Rcurve[good][-1])

# ping basina kazanc ofseti: o derinlikteki tipik su kolonu seviyesinden sapma
bb = np.round(b / 0.05) * 0.05
off = noise - pd.Series(noise).groupby(bb).transform("median").to_numpy()
exc = prof - R - off[:, None]                              # bos suya gore fazla yanki

# ------------------------------------------------------------------ 2) esik
ref = exc[(b > 2.2)[:, None] & (ZREL[None, :] >= -0.8) & (ZREL[None, :] <= -0.6)]
ref = ref[np.isfinite(ref)]
mad = 1.4826 * np.median(np.abs(ref - np.median(ref)))
T = np.median(ref) + 3 * mad
print(f"Bos su fazla-yanki dagilimi: medyan {np.median(ref):.0f}, robust sd {mad:.0f} -> esik {T:.0f}")

# ------------------------------------------------------------------ 3) ping basina olculer
w = (ZREL >= PENCERE[0]) & (ZREL <= PENCERE[1])
zw = ZREL[w]
E = exc[:, w]
valid_s = zabs[:, w] >= RINGDOWN                           # cinlama disindaki ornekler
E = np.where(valid_s, E, np.nan)
# 3 cm kayan ortalama
k = np.ones(3) / 3
Es = np.apply_along_axis(lambda r: np.convolve(np.nan_to_num(r, nan=-1e9), k, "same"), 1, E)
Es[~valid_s] = np.nan
win_len = valid_s.sum(1) * 0.01
valid_p = ok & (win_len >= MIN_PENCERE)

above = Es > T
# --- artefakt elemesi
# (a) bos su penceresi (dibin 60-80 cm ustu) de esigin ustundeyse: tum kolonu kesen parazit / gecis bozulmasi
ust = exc[:, (ZREL >= -0.8) & (ZREL <= -0.6)]
artefakt = np.nanmean(np.where(np.isfinite(ust), ust > T, False), 1) > 0.3
valid_p &= ~artefakt
# (c) tekne neredeyse dururken (< 1 km/sa) tespitler ~10 kat artiyor (seyirde bitki yine yakalanirdi):
#     manevra / pervane kaynakli bulanma ile karismasin diye bu ping'ler disarida
hiz = d["speed_ms"].where(d["speed_ms"] < 5).rolling(51, center=True, min_periods=5).median().to_numpy()
yavas = ~(hiz >= 1.0 / 3.6)
valid_p &= ~yavas
print(f"Yavas (< 1 km/sa) oldugu icin disarida birakilan ping: {(yavas & ok).sum()}")
# (b) sureklilik: bitki ardisik ping'lerde de gorunur; tek ping'lik dikey cizgiler (parazit) ve
#     gecen baliklar elensin diye 9 ping'lik (~0,35 sn, ~20 cm yol) pencerede cogunluk sarti
SUREK = 9
cs_ = np.cumsum(np.vstack([np.zeros((1, above.shape[1])), above.astype(np.float32)]), 0)
h = SUREK // 2
lo_i = np.clip(np.arange(len(b)) - h, 0, len(b))
hi_i = np.clip(np.arange(len(b)) + h + 1, 0, len(b))
above = (cs_[hi_i] - cs_[lo_i]) >= (SUREK // 2 + 1)
above &= valid_s
print(f"Artefakt olarak elenen ping: {artefakt.sum()}")
# kaplama: pencerenin ne kadari esigin ustunde
kaplama = np.where(valid_p, np.nansum(above, 1) / np.maximum(valid_s.sum(1), 1), np.nan)
# ortu yuksekligi: dipten (-0.08) yukari kesintisiz (<=2 cm bosluga izin) esik-ustu yanki
yuk = np.full(len(b), np.nan)
for i in np.where(valid_p)[0]:
    a = above[i][::-1]          # dipten yukari
    vs = valid_s[i][::-1]
    top, gap = 0, 0
    for j in range(a.size):
        if not vs[j]:
            break
        if a[j]:
            top, gap = j + 1, 0
        else:
            gap += 1
            if gap > 2:
                break
    yuk[i] = 0.0 if top == 0 else (-PENCERE[1] + top * 0.01)
d["kaplama"] = kaplama
d["ortu_yuk_m"] = yuk
d["bottom"] = b
d["gecerli"] = valid_p
v = d[d["gecerli"]]
print(f"Gecerli ping: {valid_p.sum()} / {ok.sum()}  (dip >= ~{RINGDOWN + MIN_PENCERE + 0.08:.2f} m olan yerler)")
print(f"Ortu yuksekligi > 10 cm olan ping orani: {(v['ortu_yuk_m'] > 0.10).mean():.1%}, > 25 cm: {(v['ortu_yuk_m'] > 0.25).mean():.1%}")
print(v.groupby(pd.cut(v["bottom"], [1.5, 1.8, 2.1, 2.4, 2.7, 3.3]), observed=True)[["kaplama", "ortu_yuk_m"]]
      .agg(["median", "mean"]).round(3).to_string())

# ------------------------------------------------------------------ 4) grid + 10 m yumusatma
x0, y0 = d["e"].min(), d["n"].min()
d["x"], d["y"] = d["e"] - x0, d["n"] - y0
d["gx"], d["gy"] = (d["x"] // CELL).astype(int), (d["y"] // CELL).astype(int)
v = d[d["gecerli"]]
g = v.groupby(["gx", "gy"]).agg(x=("x", "mean"), y=("y", "mean"), lat=("lat", "mean"), lon=("lon", "mean"),
                                 dep=("bottom", "median"), n=("kaplama", "size"),
                                 kaplama=("kaplama", "mean"), yuk=("ortu_yuk_m", "median"),
                                 yuk90=("ortu_yuk_m", lambda s: s.quantile(0.9))).reset_index()
g = g[g["n"] >= 5].reset_index(drop=True)
P = g[["x", "y"]].to_numpy()
W = np.exp(-((P[:, None, :] - P[None, :, :]) ** 2).sum(-1) / (2 * SIGMA ** 2)) * g["n"].to_numpy()[None, :]
for c in ["kaplama", "yuk", "yuk90"]:
    g[c + "_s"] = (W @ g[c].to_numpy()) / W.sum(1)
del W
g.drop(columns=["gx", "gy"]).to_csv(os.path.join(OUT, "bitki_grid_1m.csv"), index=False)

# tekrarlanabilirlik: 10 m hucre, kaydin 1. yarisi vs 2. yarisi
v = d[d["gecerli"]].copy()
v["Gx"], v["Gy"] = (v["x"] // 10).astype(int), (v["y"] // 10).astype(int)
v["yari"] = np.where(v["time_s"] < v["time_s"].median(), 1, 2)
A = v.groupby(["Gx", "Gy", "yari"]).agg(n=("kaplama", "size"), kap=("kaplama", "mean"),
                                        yk=("ortu_yuk_m", "median")).reset_index()
A = A[A["n"] >= 200].pivot_table(index=["Gx", "Gy"], columns="yari", values=["kap", "yk"]).dropna()
r_kap = np.corrcoef(A[("kap", 1)], A[("kap", 2)])[0, 1]
r_yk = np.corrcoef(A[("yk", 1)], A[("yk", 2)])[0, 1]
r_dep = np.corrcoef(g["kaplama_s"], g["dep"])[0, 1]
print(f"Tekrarlanabilirlik (10 m, {len(A)} ortak hucre): kaplama r={r_kap:.2f}, ortu yuksekligi r={r_yk:.2f}")
print(f"Kaplama - derinlik korelasyonu (grid): r={r_dep:.2f}")

# ------------------------------------------------------------------ 5) gorseller
# 5a) referans egrisi ve esik
fig, ax = plt.subplots(1, 2, figsize=(13, 4.5))
ax[0].plot(Rc[good], Rcurve[good], color="k")
ax[0].axvspan(0, RINGDOWN, color="red", alpha=0.12, label="verici cinlamasi (olcum yok)")
ax[0].set_xlabel("Vericiden uzaklik (m)"); ax[0].set_ylabel("Yanki (ham)")
ax[0].set_title("Bos su referansi"); ax[0].legend()
for lo, hi, c in [(1.7, 2.1, "#1b9e77"), (2.1, 2.5, "#7570b3"), (2.5, 2.7, "#d95f02"), (2.7, 3.3, "#e7298a")]:
    m = valid_p & (b >= lo) & (b < hi)
    ax[1].plot(ZREL[ZREL < 0.05], np.nanmedian(exc[m][:, ZREL < 0.05], 0), color=c, label=f"dip {lo}-{hi} m")
ax[1].axhline(T, color="k", ls="--", lw=1, label="esik")
ax[1].axvspan(PENCERE[1], 0.05, color="grey", alpha=0.15)
ax[1].set_xlabel("Tabana gore z (m)"); ax[1].set_ylabel("Bos suya gore fazla yanki")
ax[1].set_title("Dip ustu fazla yanki (medyan)"); ax[1].legend(fontsize=8)
kaydet(fig, "B0_referans_ve_dip_ustu.png")

# 5b) dibe hizali kesitler: en yuksek ve en dusuk ortulu 40 sn'lik parcalar
d["blok"] = (d["time_s"] // 40).astype(int)
bs = d[d["gecerli"]].groupby("blok").agg(kap=("kaplama", "mean"), n=("kaplama", "size"))
bs = bs[bs["n"] > 500].sort_values("kap")
secim = list(bs.index[-3:][::-1]) + list(bs.index[:2])
fig, axs = plt.subplots(len(secim), 1, figsize=(14, 2.3 * len(secim)), sharex=False)
vis = (ZREL >= -0.8) & (ZREL <= 0.4)
lo_, hi_ = np.nanpercentile(prof[valid_p][:, vis], [3, 99.5])
for ax, bl in zip(axs, secim):
    ii = np.where((d["blok"] == bl).to_numpy())[0]
    ax.imshow(prof[ii][:, vis].T, aspect="auto", cmap="copper", vmin=lo_, vmax=hi_,
              extent=[0, len(ii), ZREL[vis][-1], ZREL[vis][0]])
    ax.axhline(0, color="cyan", lw=0.4)
    ax.plot(np.arange(len(ii)), -d["ortu_yuk_m"].to_numpy()[ii], color="lime", lw=0.6)
    t0 = d["time_s"].iloc[ii[0]] / 60
    ax.set_ylabel("m (0=dip)")
    ax.set_title(f"{t0:.1f}. dk - derinlik {np.nanmedian(b[ii]):.2f} m - ortalama kaplama %{100 * bs.loc[bl, 'kap']:.0f}",
                 fontsize=10, loc="left")
    ax.set_xticks([])
fig.suptitle("Dibe hizali sonar kesitleri: ust 3 = en yuksek bitki skoru, alt 2 = en dusuk  (yesil cizgi: olculen ortu ust siniri)",
             fontsize=11)
kaydet(fig, "B1_ornek_kesitler.png")

# 5c) uydu uzerinde haritalar
from uydu_altlik import Mozaik, merc, kontur_seviyeleri
_moz = Mozaik()
mos, EXT = _moz.img, _moz.ext
kk = 1 / math.cos(math.radians(d["lat"].mean()))
g["mx"], g["my"] = merc(g["lat"], g["lon"])
rx, ry = merc(d["lat"].to_numpy(), d["lon"].to_numpy())
VIEW = [rx.min() - 25 * kk, rx.max() + 25 * kk, ry.min() - 25 * kk, ry.max() + 25 * kk]
t = mtri.Triangulation(g["mx"], g["my"])
p = np.c_[g["mx"], g["my"]][t.triangles]
e = np.max([np.hypot(*(p[:, i] - p[:, (i + 1) % 3]).T) for i in range(3)], axis=0)
t.set_mask(e > MAX_EDGE * kk)

fig, axs = plt.subplots(1, 2, figsize=(18, 10.5))
for ax, col, ttl, cmap, lab, scale in [
        (axs[0], "kaplama_s", "Bitki kaplama orani\n(dibin 8-50 cm ustunde bos sudan belirgin yanki veren kisim)",
         "YlGn", "kaplama (%)", 100),
        (axs[1], "yuk90_s", "Ortu yuksekligi (en uzun %10)\n(dipten yukari kesintisiz yanki)", "BuGn", "yukseklik (cm)", 100)]:
    ax.imshow(np.asarray(mos), extent=EXT, origin="upper")
    vals = g[col].to_numpy() * scale
    lv = np.linspace(np.nanpercentile(vals, 2), np.nanpercentile(vals, 98), 11)
    if not np.all(np.diff(lv) > 0):
        lv = np.linspace(0, max(float(np.nanmax(vals)), 1.0), 11)
    cf = ax.tricontourf(t, np.clip(vals, lv[0], lv[-1]), levels=lv, cmap=cmap, alpha=0.75)
    cs = ax.tricontour(t, g["dep"], levels=kontur_seviyeleri(g["dep"]), colors="white", linewidths=0.7)
    ax.clabel(cs, fmt="%.1f m", fontsize=8, colors="white")
    plt.colorbar(cf, ax=ax, shrink=0.55, label=lab)
    ax.plot(rx[::20], ry[::20], color="k", lw=0.2, alpha=0.4)
    ax.set_xlim(VIEW[:2]); ax.set_ylim(VIEW[2:]); ax.set_aspect("equal")
    ax.set_xticks([]); ax.set_yticks([]); ax.set_title(ttl, fontsize=11)
    ax.text(0.99, 0.005, "Uydu: Esri World Imagery", transform=ax.transAxes, ha="right", va="bottom",
            fontsize=7, color="white")
fig.suptitle(f"Su bitkisi ortusu tahmini: anlamli ortu tespit edilmedi (~10 m olcek; tekne < 1 km/sa ve derinlik < ~1,6 m disarida) - "
             f"tekrarlanabilirlik r={r_kap:.2f}", fontsize=12)
kaydet(fig, "B2_uydu_bitki_haritasi.png")
