"""Tek isinli (down-scan) sonar kaydindan akustik zemin siniflandirmasi.

Her ping icin taban yankisinin seklinden goreli oznitelikler cikarilir,
1 m'lik grid'e toplanir, haritalanir ve k-means ile kumelenir.

ONEMLI: Bu GORELI bir siniflamadir. Kalibre edilmemis bir eko-sounder ile
"burasi kesin camur" denemez; siniflar dip numunesi (grab) ile dogrulanmalidir.

Kullanim:  .venv\\Scripts\\python zemin.py
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.tri as mtri

RSD = "Sonar000.RSD"
META = "cozumleme/meta/B001_ds_hifreq_meta.csv"
OUT = "cozumleme/zemin"
CELL = 1.0
MAX_EDGE = 7.0
DZ = 0.01                      # tabana gore yeniden orneklenmis profil adimi (m)
ZREL = np.arange(-0.8, 2.5, DZ)  # tabana gore bagil derinlik ekseni
os.makedirs(OUT, exist_ok=True)

def _kaydet(fig, yol, dpi):
    """Windows'ta mevcut PNG uzerine yazma bazen Errno 22 verdiginden once eskisini sil."""
    if os.path.exists(yol):
        os.remove(yol)
    fig.savefig(yol, dpi=dpi)


# ------------------------------------------------------------------ veri
d = pd.read_csv(META)
has = d["inst_dep_m"].notna()
seg = (has.astype(int).diff() != 0).cumsum()
d = d[has & (has.groupby(seg).transform("sum") >= 1000)].copy().reset_index(drop=True)
d["dsm"] = d["inst_dep_m"].rolling(51, center=True, min_periods=10).median()


def movavg(a, k):
    return np.convolve(a, np.ones(k) / k, mode="same")


# ------------------------------------------------------------------ ping basina oznitelik
n = len(d)
feat = {k: np.full(n, np.nan, np.float32) for k in
        ["bottom", "noise", "peak", "rise", "tail", "decay", "e2", "above"]}
prof = np.full((n, ZREL.size), np.nan, np.float32)
CACHE = os.path.join(OUT, "_ping_oznitelik_onbellek.npz")   # silinirse yeniden hesaplanir

if os.path.exists(CACHE):
    z_ = np.load(CACHE)
    feat = {k: z_[k] for k in feat}
    prof = z_["prof"]
    print("Onbellekten yuklendi:", CACHE)

with open(RSD, "rb") as f:
    for i, r in enumerate(d.itertuples() if not os.path.exists(CACHE) else []):
        f.seek(int(r.index) + int(r.son_offset))
        a = np.frombuffer(f.read(int(r.ping_cnt) * 2), "<u2").astype(np.float32)
        if a.size != r.ping_cnt or not np.isfinite(r.dsm):
            continue
        dz = r.max_range / a.size
        s = movavg(a, 5)
        # --- tabani hassaslastir: tahmini derinlik +-0.35 m icinde en dik yukselis
        lo = max(int((r.dsm - 0.35) / dz), 10)
        hi = min(int((r.dsm + 0.35) / dz), a.size - 10)
        if hi - lo < 10:
            continue
        g = s[lo + 3:hi + 3] - s[lo - 3:hi - 3]
        b = lo + int(np.argmax(g))
        bz = b * dz
        # --- su kolonu gurultu tabani (kazanc farklarini sifirlamak icin referans)
        w0, w1 = int(0.45 * b), int(0.85 * b)
        if w1 - w0 < 10:
            continue
        noise = np.median(a[w0:w1])
        an = a - noise                      # gurultuye gore bagil (log olcekte = dB farki benzeri)

        def win(z0, z1):
            i0, i1 = b + int(z0 / dz), b + int(z1 / dz)
            if i0 < 0 or i1 > a.size or i1 <= i0:
                return None
            return an[i0:i1]

        pk = win(0.0, 0.15)
        tl = win(0.15, 0.60)
        dc = win(0.10, 1.50)
        ab = win(-0.60, -0.10)
        if pk is None or tl is None or ab is None:
            continue
        feat["bottom"][i] = bz
        feat["noise"][i] = noise
        feat["peak"][i] = np.percentile(pk, 90)              # taban yankisi gucu -> sertlik
        # yukselis keskinligi: tabandan once/sonra 5 cm ortalama farki / 5 cm
        pre = win(-0.06, -0.01)
        feat["rise"][i] = (pk[: int(0.05 / dz)].mean() - pre.mean()) if pre is not None else np.nan
        feat["tail"][i] = tl.mean()                          # taban sonrasi kuyruk -> hacim sacilmasi / penetrasyon
        if dc is not None:
            zz = np.arange(dc.size) * dz
            feat["decay"][i] = -np.polyfit(zz, movavg(dc, 9), 1)[0]   # kuyruk sonumlenme hizi (birim/m)
        e2 = win(bz - 0.15, bz + 0.15)                        # ikinci yanki: 2x derinlik
        if e2 is not None and e2.size > 5:
            feat["e2"][i] = np.percentile(e2, 90)
        feat["above"][i] = np.percentile(ab, 75)              # tabanin hemen ustundeki yanki -> bitki / askida tabaka
        # tabana gore hizalanmis profil (kesit gorselleri icin)
        z = np.arange(a.size) * dz - bz
        prof[i] = np.interp(ZREL, z, an, left=np.nan, right=np.nan)

if not os.path.exists(CACHE):
    np.savez(CACHE, prof=prof, **feat)

for k, v in feat.items():
    d[k] = v.astype(np.float64)
# Su kolonu "gurultu" referansi derinlikle guclu degisiyor (sig yerde verici cinlamasina denk geliyor).
# Cihaz zaten TVG uyguladigi icin MUTLAK yanki degerleri derinlikten bagimsiza yakin -> mutlak degerlere don.
for k in ["peak", "tail", "e2", "above"]:
    d[k] = d[k] + d["noise"]
d["contrast"] = d["tail"] - d["peak"]       # kuyruk / tepe orani (log olcekte fark): penetrasyon gostergesi
d.loc[d["bottom"] < 1.5, "above"] = np.nan  # cok sigda pencere verici cinlamasina giriyor
prof += feat["noise"][:, None]
d = d.dropna(subset=["peak", "tail"])
print("Islenen ping:", len(d))
print("Taban secimi - cihaz derinligi farki (m): medyan %.3f, IQR %.3f" %
      ((d["bottom"] - d["dsm"]).median(), (d["bottom"] - d["dsm"]).quantile(.75) - (d["bottom"] - d["dsm"]).quantile(.25)))
print("Kazanc ile korelasyon:")
print(d[["gain", "dsm", "noise", "peak", "rise", "tail", "decay", "e2", "above"]].corr()["gain"].round(2).to_string())

# Otomatik kazanc (gain) degisimlerinin etkisini temizle: oznitelik ~ a*gain + b*derinlik + c
# regresyonu kurup yalnizca gain teriminin katkisini cikariyoruz (derinlik etkisi gercek olabilir, korunur).
G = np.c_[d["gain"] - d["gain"].median(), d["dsm"] - d["dsm"].median(), np.ones(len(d))]
for k in ["peak", "rise", "tail", "contrast", "decay", "e2", "above"]:
    m = d[k].notna().values
    coef, *_ = np.linalg.lstsq(G[m], d.loc[m, k].values, rcond=None)
    d.loc[m, k] = d.loc[m, k] - coef[0] * G[m, 0]
print("Gain duzeltmesi sonrasi korelasyon:")
print(d[["gain", "dsm", "peak", "tail", "contrast", "decay", "e2", "above"]].corr()[["gain", "dsm"]].round(2).to_string())

# ------------------------------------------------------------------ grid
x0, y0 = d["e"].min(), d["n"].min()
d["x"], d["y"] = d["e"] - x0, d["n"] - y0
d["gx"], d["gy"] = (d["x"] // CELL).astype(int), (d["y"] // CELL).astype(int)
F = ["peak", "rise", "tail", "contrast", "decay", "above"]
g = d.groupby(["gx", "gy"]).agg(x=("x", "mean"), y=("y", "mean"), lat=("lat", "mean"), lon=("lon", "mean"),
                                 dep=("dsm", "median"), n=("peak", "size"),
                                 **{k: (k, "median") for k in F + ["e2"]}).reset_index()
g = g[g["n"] >= 5].reset_index(drop=True)
g["above"] = g["above"].fillna(g["above"].median())

tri = mtri.Triangulation(g["x"], g["y"])
p = np.c_[g["x"], g["y"]][tri.triangles]
edges = np.max([np.hypot(*(p[:, i] - p[:, (i + 1) % 3]).T) for i in range(3)], axis=0)
tri.set_mask(edges > MAX_EDGE)


def mapplot(ax, col, title, cmap, lab):
    v = g[col].values
    lv = np.linspace(*np.nanpercentile(v, [3, 97]), 12)
    cf = ax.tricontourf(tri, np.clip(v, lv[0], lv[-1]), levels=lv, cmap=cmap, extend="both")
    ax.tricontour(tri, g["dep"], levels=np.arange(1.0, 3.5, 0.5), colors="k", linewidths=0.4, alpha=0.5)
    plt.colorbar(cf, ax=ax, shrink=0.8, label=lab)
    ax.set_title(title, fontsize=10)
    ax.set_aspect("equal")
    ax.set_xticks([]); ax.set_yticks([])


# Sonumlenme derinlikle geometrik olarak da degisir (derinde dipte aydinlanan alan buyur, kuyruk uzar).
# Bu etkiyi ayirmak icin derinlige dogrusal uyum yapip artik (residual) degeri kullaniyoruz.
cf_ = np.polyfit(g["dep"], g["decay"], 1)
g["decay_res"] = g["decay"] - np.polyval(cf_, g["dep"])

# Kesisim testi: 2 m olcekte ayni hucreye farkli gecislerin oznitelikleri tutarsiz (r ~ 0.1-0.4),
# 10 m olcekte tutarli (r ~ 0.6-0.75). Bu yuzden oznitelikleri ~10 m olcekte yumusatiyoruz.
SIGMA = 4.0   # Gauss yumusatma (m); etkin cap ~10 m
P = g[["x", "y"]].to_numpy()
W = np.exp(-((P[:, None, :] - P[None, :, :]) ** 2).sum(-1) / (2 * SIGMA ** 2)) * g["n"].to_numpy()[None, :]
for k in ["peak", "contrast", "decay", "decay_res"]:
    v = g[k].to_numpy()
    m = np.isfinite(v)
    g[k] = (W[:, m] @ v[m]) / W[:, m].sum(1)
del W

fig, axs = plt.subplots(2, 2, figsize=(14, 15))
mapplot(axs[0, 0], "peak", "1) Taban yankisi gucu  ->  SERTLIK\n(yuksek = sert/sikismis, dusuk = yumusak camur)",
        "YlOrBr", "yanki siddeti")
mapplot(axs[0, 1], "contrast", "2) Kuyruk - tepe farki  ->  PENETRASYON\n(yuksek = ses tortuya giriyor: gevsek birikinti)",
        "PuBu", "fark")
mapplot(axs[1, 0], "decay", "3) Kuyruk sonumlenme hizi (ham)\n(dusuk = kalin yumusak tabaka; derinlikten de etkilenir)",
        "RdYlGn", "birim / m")
mapplot(axs[1, 1], "decay_res", "4) Sonumlenme - derinlik etkisi cikarilmis\n(negatif = beklenenden yavas: kalin yumusak tortu)",
        "RdYlGn", "birim / m")
fig.suptitle("Akustik zemin oznitelikleri, ~10 m olcekte yumusatilmis (siyah cizgiler: 0,5 m derinlik konturlari)",
             fontsize=13)
fig.tight_layout()
_kaydet(fig, os.path.join(OUT, "6_zemin_oznitelik_haritalari.png"), 130)
plt.close(fig)

# ------------------------------------------------------------------ k-means (numpy)
X = g[["peak", "contrast", "decay_res"]].to_numpy(float)
X = (X - np.nanmedian(X, 0)) / (np.nanpercentile(X, 75, 0) - np.nanpercentile(X, 25, 0))
ok = np.isfinite(X).all(1)
K = 3
rng = np.random.default_rng(0)
best = None
for _ in range(20):
    C = X[ok][rng.choice(ok.sum(), K, replace=False)]
    for _ in range(100):
        lab = np.argmin(((X[ok][:, None] - C[None]) ** 2).sum(-1), 1)
        Cn = np.array([X[ok][lab == k].mean(0) if (lab == k).any() else C[k] for k in range(K)])
        if np.allclose(Cn, C):
            break
        C = Cn
    inertia = ((X[ok] - C[lab]) ** 2).sum()
    if best is None or inertia < best[0]:
        best = (inertia, lab.copy(), C.copy())
_, lab, C = best
g["sinif"] = -1
g.loc[ok, "sinif"] = lab

# siniflari "sertlik skoru"na gore sirala: tepe guclu + hizli sonum + dusuk penetrasyon = sert
score = C[:, 0] + C[:, 2] - C[:, 1]
order = np.argsort(score)                 # yumusaktan serte
remap = {old: new for new, old in enumerate(order)}
g.loc[ok, "sinif"] = g.loc[ok, "sinif"].map(remap)
C = C[order]
names = ["Yumusak camur birikintisi (ses tortuya giriyor)", "Orta: silt / ince camur",
         "Daha siki / sert zemin"]
summ = g[ok].groupby("sinif").agg(hucre=("x", "size"), derinlik=("dep", "median"),
                                  sertlik=("peak", "median"), penetrasyon=("contrast", "median"),
                                  sonum=("decay", "median"), ust=("above", "median"))
summ["yorum"] = names
summ["alan_yuzde"] = (100 * summ["hucre"] / summ["hucre"].sum()).round(1)
print(summ.round(2).to_string())
summ.round(3).to_csv(os.path.join(OUT, "zemin_sinif_ozeti.csv"))

cols = ["#8c510a", "#dfc27d", "#35978f"]
fig, ax = plt.subplots(figsize=(11, 12))
gg = g[ok]
from matplotlib.colors import ListedColormap, BoundaryNorm
cm = ListedColormap(cols)
ax.tricontourf(tri, g["sinif"].clip(0).astype(float), levels=np.arange(-0.5, K), cmap=cm)
ax.plot(d["x"], d["y"], color="k", lw=0.2, alpha=0.25)
cs = ax.tricontour(tri, g["dep"], levels=np.arange(1.0, 3.5, 0.5), colors="k", linewidths=0.6)
ax.clabel(cs, fmt="%.1f m", fontsize=8)
for k in range(K):
    ax.scatter([], [], c=cols[k], marker="s", s=80,
               label=f"Sinif {k}: {names[k]} ({summ.loc[k, 'alan_yuzde']}%)")
ax.legend(loc="lower left", fontsize=9, framealpha=0.9)
ax.set_aspect("equal")
ax.set_xlabel("Dogu (m)"); ax.set_ylabel("Kuzey (m)")
ax.set_title("Akustik zemin siniflari (k-means, goreli - dip numunesiyle dogrulanmali)")
fig.tight_layout()
_kaydet(fig, os.path.join(OUT, "7_zemin_siniflari.png"), 130)
plt.close(fig)

# ------------------------------------------------------------------ tabana hizali kesit (birikinti/tabaka gorunumu)
fig, axs = plt.subplots(2, 1, figsize=(16, 9))
step = max(1, len(d) // 3000)
pp = prof[d.index.values][::step].T
lo, hi = np.nanpercentile(pp, [5, 99.5])
axs[0].imshow(pp, aspect="auto", cmap="copper", vmin=lo, vmax=hi,
              extent=[d["time_s"].iloc[0] / 60, d["time_s"].iloc[-1] / 60, ZREL[-1], ZREL[0]])
axs[0].axhline(0, color="cyan", lw=0.5)
axs[0].set_ylabel("Tabana gore derinlik (m)\n(0 = dip yuzeyi)")
axs[0].set_title("Tabana hizalanmis echogram: dibin altina ne kadar ses giriyor (birikinti / tabaka)")
axs[0].set_xlabel("Sure (dk)")
for k in range(K):
    cells = g.loc[g["sinif"] == k, ["gx", "gy"]]
    sel = d.assign(_row=d.index).merge(cells, on=["gx", "gy"])["_row"].values
    mp = np.nanmean(prof[sel], 0)
    axs[1].plot(ZREL, mp, color=cols[k], lw=1.5, label=f"Sinif {k}: {names[k]}")
axs[1].axvline(0, color="k", lw=0.5)
axs[1].set_xlabel("Tabana gore derinlik (m)  (negatif = su kolonu, pozitif = dip alti)")
axs[1].set_ylabel("Yanki siddeti (ham, log olcek)")
axs[1].set_title("Siniflarin ortalama yanki profili")
axs[1].legend(fontsize=9)
fig.tight_layout()
_kaydet(fig, os.path.join(OUT, "8_tabana_hizali_kesit_ve_profiller.png"), 130)
plt.close(fig)

g.drop(columns=["gx", "gy"]).to_csv(os.path.join(OUT, "zemin_grid_1m.csv"), index=False)
print("Bitti ->", OUT)
