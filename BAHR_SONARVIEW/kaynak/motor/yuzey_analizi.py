"""Kot-alan-hacim tablosu ve belirsizlik haritasi.

Veri: uydu analizi yapildiysa tum su alani (cozumleme/morfoloji/tum_golet_grid.csv), yoksa yalnizca
olculen alan (cozumleme/grafikler/derinlik_izgara.npz).

Belirsizlik (tahmini, 1 sigma):
  sigma = sqrt( (0.05 + 0.01*derinlik)^2 + (egim * uzaklik)^2 + model^2 )
  - ilk terim  : tek isinli sonarin olcum belirsizligi (yaklasik)
  - ikinci     : ara degerleme hatasi; dip ne kadar egimli ve olcume ne kadar uzaksa o kadar buyuk
  - model      : olcum hattindan 7 m'den uzak (kiyi varsayimiyla doldurulan) yerlerde 0,15 m
Ciktilar: cozumleme/hacim/  kot_alan_hacim.csv, K1_kot_alan_hacim.png, B1_belirsizlik.png
          cozumleme/web/    hacim_tablosu.json, katman_belirsizlik.json, belirsizlik.png
"""
import json
import os

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from pyproj import CRS, Transformer  # noqa: E402

from katmanlar import raster, yaz  # noqa: E402
from ortak import kaydet_png, parametreler  # noqa: E402

P = parametreler()
OUT = "cozumleme/hacim"
os.makedirs(OUT, exist_ok=True)
SU_KOTU = float(P.get("su_kotu") or 0.0)

npz = np.load("cozumleme/grafikler/derinlik_izgara.npz")
Z, N = npz["Z"].astype(float), npz["N"]
x0, y1, h, epsg = float(npz["x0"]), float(npz["y1"]), float(npz["hucre"]), int(npz["epsg"])
ny, nx = Z.shape
crs = CRS.from_epsg(epsg)
ll2xy = Transformer.from_crs(4326, crs, always_xy=True)
xy2ll = Transformer.from_crs(crs, 4326, always_xy=True)

TUM = "cozumleme/morfoloji/tum_golet_grid.csv"
if os.path.exists(TUM):
    tg = pd.read_csv(TUM)
    px, py = ll2xy.transform(tg["lon"].to_numpy(), tg["lat"].to_numpy())
    dep = tg["derinlik"].to_numpy(float)
    alan_hucre = 1.0                       # morfoloji izgarasi 1 m x 1 m (yer metresi)
    kapsam = "tüm su alanı (uydudan kıyı çizgisiyle)"
else:
    r, c = np.nonzero(np.isfinite(Z))
    px = x0 + (c + 0.5) * h
    py = y1 - (r + 0.5) * h
    dep = Z[r, c]
    alan_hucre = h * h
    kapsam = "yalnızca ölçülen alan"

# ---------------------------------------------------------------- uzaklik: en yakin olcume (m)
# ortak UTM rasteri: olculen hucreler N>0; 8-komsu genisletmeyle uzaklik (en cok 150 m)
X0 = min(x0, px.min()) - 2
Y1 = max(y1, py.max()) + 2
W = int(np.ceil((max(x0 + nx * h, px.max()) + 2 - X0) / h))
H = int(np.ceil((Y1 - min(y1 - ny * h, py.min()) + 2) / h))
olc = np.zeros((H, W), bool)
rr, cc = np.nonzero(N > 0)
olc[np.clip(((Y1 - (y1 - (rr + 0.5) * h)) / h).astype(int), 0, H - 1),
    np.clip(((x0 + (cc + 0.5) * h - X0) / h).astype(int), 0, W - 1)] = True
UZ = np.full((H, W), np.inf, np.float32)
UZ[olc] = 0
cur = olc.copy()
for k in range(1, 151):
    yeni = cur.copy()
    yeni[1:] |= cur[:-1]; yeni[:-1] |= cur[1:]; yeni[:, 1:] |= cur[:, :-1]; yeni[:, :-1] |= cur[:, 1:]
    yeni[1:, 1:] |= cur[:-1, :-1]; yeni[:-1, :-1] |= cur[1:, 1:]; yeni[1:, :-1] |= cur[:-1, 1:]; yeni[:-1, 1:] |= cur[1:, :-1]
    UZ[yeni & ~cur] = k * h
    if yeni.sum() == cur.sum():
        break
    cur = yeni
pr = np.clip(((Y1 - py) / h).astype(int), 0, H - 1)
pc = np.clip(((px - X0) / h).astype(int), 0, W - 1)
uz = UZ[pr, pc]
uz[~np.isfinite(uz)] = 150.0
print("@@ilerleme 0.4", flush=True)

# ---------------------------------------------------------------- egim (yerel derinlik gradyani)
D = np.full((H, W), np.nan)
D[pr, pc] = dep
Dd = np.where(np.isfinite(D), D, 0.0)
Wt = np.isfinite(D).astype(float)
for _ in range(2):                         # 3x3 ortalama ile yumusat (NaN'lara dikkat)
    def kutu(a):
        b = np.pad(a, 1, mode="edge")
        return sum(b[i:i + a.shape[0], j:j + a.shape[1]] for i in range(3) for j in range(3)) / 9
    Dd, Wt = kutu(Dd), kutu(Wt)
Ds = np.where(Wt > 0.05, Dd / np.maximum(Wt, 1e-6), np.nan)
gy, gx = np.gradient(Ds, h)
G = np.hypot(gx, gy)
eg = np.nan_to_num(G[pr, pc], nan=float(np.nanmedian(G)) if np.isfinite(G).any() else 0.02)
eg = np.clip(eg, 0, 0.5)
ara = np.minimum(eg * uz, np.maximum(0.3, 0.5 * dep))     # ara degerleme hatasi yerel derinligin yarisini asmaz
sigma = np.sqrt((0.05 + 0.01 * dep) ** 2 + ara ** 2 + np.where(uz > 7, 0.15, 0.0) ** 2)

sinif_sinir = [1.0, 3.0, 7.0]
sinif_ad = ["Ölçüldü (≤1 m)", "Ölçüme yakın (1–3 m)", "Ara değer (3–7 m)", "Tahmin (>7 m)"]
sinif = np.digitize(uz, sinif_sinir, right=True)
pay = [round(100 * float((sinif == i).mean()), 1) for i in range(4)]

# ---------------------------------------------------------------- kot - alan - hacim
taban = SU_KOTU - dep
lo = float(np.floor(np.nanmin(taban) * 10) / 10)
aralik = SU_KOTU - lo
adim = 0.1 if aralik <= 4 else 0.25 if aralik <= 10 else 0.5 if aralik <= 25 else 1.0
kotlar = np.round(np.arange(lo, SU_KOTU + adim / 2, adim), 3)
if kotlar[-1] < SU_KOTU - 1e-9:
    kotlar = np.append(kotlar, SU_KOTU)
tablo = pd.DataFrame({
    "kot_m": kotlar,
    "su_derinligi_m": np.round(SU_KOTU - kotlar, 3),
    "alan_m2": [float((taban < k + 1e-6).sum() * alan_hucre) for k in kotlar],
    "hacim_m3": [float(np.clip(k - taban, 0, None).sum() * alan_hucre) for k in kotlar],
})
tablo["alan_m2"] = tablo["alan_m2"].round(0)
tablo["hacim_m3"] = tablo["hacim_m3"].round(0)
tablo.to_csv(os.path.join(OUT, "kot_alan_hacim.csv"), index=False, encoding="utf-8-sig")
hacim_sigma = float(np.sqrt(((sigma * alan_hucre) ** 2).sum() * 25))    # ~5 m korelasyon uzunlugu varsayimi
ozet = {
    "kapsam": kapsam, "su_kotu": SU_KOTU, "toplam_alan_m2": round(float(dep.size * alan_hucre)),
    "toplam_hacim_m3": round(float(dep.sum() * alan_hucre)), "hacim_belirsizlik_m3": round(hacim_sigma),
    "sigma_medyan_cm": round(float(np.median(sigma) * 100), 1), "sigma_p90_cm": round(float(np.percentile(sigma, 90) * 100), 1),
    "sinif_ad": sinif_ad, "sinif_yuzde": pay,
    "tablo": {k: tablo[k].tolist() for k in tablo.columns},
}
yaz("hacim_tablosu.json", ozet)

# ---------------------------------------------------------------- gorseller
fig, ax = plt.subplots(figsize=(10, 6))
ax.plot(tablo["alan_m2"], tablo["kot_m"], color="#0e7490", lw=2, label="Alan (m²)")
ax.set_xlabel("Su yüzeyi alanı (m²)", color="#0e7490")
ax.set_ylabel("Kot (m)" + ("" if SU_KOTU else "  — su yüzeyi = 0"))
ax2 = ax.twiny()
ax2.plot(tablo["hacim_m3"], tablo["kot_m"], color="#b45309", lw=2, label="Hacim (m³)")
ax2.set_xlabel("Hacim (m³)", color="#b45309")
ax.grid(alpha=0.3)
ax.set_title(f"Kot – alan – hacim eğrisi ({kapsam})", pad=34)
fig.tight_layout()
kaydet_png(fig, os.path.join(OUT, "K1_kot_alan_hacim.png"))
plt.close(fig)

lon, lat = xy2ll.transform(px, py)
fig, axs = plt.subplots(1, 2, figsize=(15, 7))
s0 = axs[0].scatter(px - X0, py - (Y1 - H * h), c=sigma * 100, s=3, cmap="magma_r", vmin=0, vmax=float(np.percentile(sigma * 100, 98)))
fig.colorbar(s0, ax=axs[0], label="tahmini belirsizlik (± cm)")
axs[0].set_title(f"Derinlik belirsizliği — ortanca ±{ozet['sigma_medyan_cm']} cm")
renk = ["#16a34a", "#84cc16", "#f59e0b", "#dc2626"]
axs[1].scatter(px - X0, py - (Y1 - H * h), c=[renk[i] for i in sinif], s=3)
for i, a in enumerate(sinif_ad):
    axs[1].scatter([], [], c=renk[i], label=f"{a}: %{pay[i]}")
axs[1].legend(loc="upper left", fontsize=9)
axs[1].set_title("Ölçüme uzaklık")
for a in axs:
    a.set_aspect("equal")
    a.set_xlabel("Doğu (m)")
    a.set_ylabel("Kuzey (m)")
fig.tight_layout()
kaydet_png(fig, os.path.join(OUT, "B1_belirsizlik.png"))
plt.close(fig)

k = raster(lat, lon, sigma * 100, "belirsizlik.png", "magma_r", 0.0, float(np.percentile(sigma * 100, 98)),
           max_kenar=3.0 if os.path.exists(TUM) else 7.0, alpha=0.78)
k.update({"min": 0, "max": round(float(np.percentile(sigma * 100, 98)), 1)})
yaz("katman_belirsizlik.json", k)
print(json.dumps({a: b for a, b in ozet.items() if a != "tablo"}, ensure_ascii=False))
print("@@ilerleme 1.0", flush=True)
