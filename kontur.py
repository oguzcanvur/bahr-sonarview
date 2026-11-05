"""Sonar derinlik okumalarindan batimetri (derinlik konturu) haritasi uretir.

Kullanim:  .venv\\Scripts\\python kontur.py
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.tri as mtri

META = "cozumleme/meta/B001_ds_hifreq_meta.csv"
OUT = "cozumleme/grafikler"
CELL = 1.0        # grid hucre boyu (m)
MAX_EDGE = 7.0    # bundan uzun ucgen kenarlari = veri yok, haritada bos birak
os.makedirs(OUT, exist_ok=True)

def _kaydet(fig, yol, dpi):
    """Windows'ta mevcut PNG uzerine yazma bazen Errno 22 verdiginden once eskisini sil."""
    if os.path.exists(yol):
        os.remove(yol)
    fig.savefig(yol, dpi=dpi)


d = pd.read_csv(META)

# 1) Kisa, kopuk derinlik bolumlerini at (5. ve 55. dk: ikinci yankiyi taban sanan hatali okumalar)
has = d["inst_dep_m"].notna()
seg = (has.astype(int).diff() != 0).cumsum()
seg_len = has.groupby(seg).transform("sum")
d = d[has & (seg_len >= 1000)].copy()

# 2) Ping-ping gurultuyu temizle: ~2 sn'lik kayan medyan
d["dep"] = d["inst_dep_m"].rolling(51, center=True, min_periods=10).median()

# 3) Hareketsiz anlarda ayni noktaya yigilan okumalar grid medyaniyla dengelenir
x0, y0 = d["e"].min(), d["n"].min()
d["x"] = d["e"] - x0
d["y"] = d["n"] - y0
d["gx"] = (d["x"] // CELL).astype(int)
d["gy"] = (d["y"] // CELL).astype(int)
g = d.groupby(["gx", "gy"]).agg(x=("x", "mean"), y=("y", "mean"),
                                 dep=("dep", "median"), n=("dep", "size")).reset_index()
g = g.dropna(subset=["dep"])

# 4) Ucgenleme + veri olmayan bosluklari maskele
tri = mtri.Triangulation(g["x"], g["y"])
p = np.c_[g["x"], g["y"]][tri.triangles]
edges = np.max([np.hypot(*(p[:, i] - p[:, (i + 1) % 3]).T) for i in range(3)], axis=0)
tri.set_mask(edges > MAX_EDGE)

levels = np.arange(np.floor(g["dep"].min() * 4) / 4, g["dep"].max() + 0.25, 0.25)
fig, ax = plt.subplots(figsize=(10, 12))
cf = ax.tricontourf(tri, g["dep"], levels=levels, cmap="Blues")
cs = ax.tricontour(tri, g["dep"], levels=np.arange(1.0, 3.5, 0.5), colors="k", linewidths=0.6)
ax.clabel(cs, fmt="%.1f m", fontsize=8)
ax.plot(d["x"], d["y"], color="red", lw=0.3, alpha=0.4, label="Tekne rotasi")
fig.colorbar(cf, ax=ax, label="Derinlik (m)", shrink=0.7)
ax.set_aspect("equal")
ax.set_xlabel(f"Dogu (m)  [UTM 36N, E0={x0:.0f}]")
ax.set_ylabel(f"Kuzey (m)  [N0={y0:.0f}]")
ax.set_title("Batimetri - derinlik konturlari (renk 0,25 m, cizgi 0,5 m aralik)")
ax.legend(loc="lower right")
fig.tight_layout()
_kaydet(fig, os.path.join(OUT, "5_batimetri_kontur.png"), 150)
plt.close(fig)

# 5) Grid noktalarini disa aktar (enlem/boylam ile)
grid = d.groupby(["gx", "gy"]).agg(lat=("lat", "mean"), lon=("lon", "mean"),
                                    derinlik_m=("dep", "median"), ping_sayisi=("dep", "size")).reset_index()
grid.dropna(subset=["derinlik_m"]).drop(columns=["gx", "gy"]).to_csv(
    os.path.join(OUT, "batimetri_grid_1m.csv"), index=False)

print(f"Grid hucresi: {len(g)}  derinlik {g['dep'].min():.2f}-{g['dep'].max():.2f} m, "
      f"medyan {g['dep'].median():.2f} m")
a, b, c = p[:, 0], p[:, 1], p[:, 2]
area = 0.5 * np.abs((b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (c[:, 0] - a[:, 0]) * (b[:, 1] - a[:, 1]))
print(f"Haritalanan alan ~{area[~tri.mask].sum():.0f} m2")
