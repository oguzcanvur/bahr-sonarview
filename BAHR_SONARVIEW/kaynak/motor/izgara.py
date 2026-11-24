"""Duzenli derinlik izgarasi (UTM, 1 m) - disa aktarma, hacim tablosu, profil ve degisim analizinin ortak verisi.

Cikti: cozumleme/grafikler/derinlik_izgara.npz
  Z    : derinlik (m), satir 0 = kuzey; olculmeyen / ara degerlenemeyen hucreler NaN
  N    : hucredeki ping sayisi (0 = ara degerlendi)
  x0, y1, hucre, epsg : sol-ust kose (UTM) ve hucre boyu
"""
import os

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.tri as mtri  # noqa: E402
from pyproj import Transformer  # noqa: E402

from ortak import META, guvenilir_dip, utm_crs  # noqa: E402

HUCRE = 1.0
MAX_KENAR = 7.0
OUT = "cozumleme/grafikler"
os.makedirs(OUT, exist_ok=True)

d = pd.read_csv(META)
d = d[guvenilir_dip(d) & (d["lat"].abs() > 0.01)].copy()
d["dep"] = d["inst_dep_m"].rolling(51, center=True, min_periods=10).median()
d = d.dropna(subset=["dep"])
crs = utm_crs(float(d["lon"].median()), float(d["lat"].median()))
tr = Transformer.from_crs(4326, crs, always_xy=True)
d["x"], d["y"] = tr.transform(d["lon"].to_numpy(), d["lat"].to_numpy())

x0 = np.floor(d["x"].min() / HUCRE) * HUCRE - 2 * HUCRE
y0 = np.floor(d["y"].min() / HUCRE) * HUCRE - 2 * HUCRE
d["ix"] = ((d["x"] - x0) // HUCRE).astype(int)
d["iy"] = ((d["y"] - y0) // HUCRE).astype(int)
g = d.groupby(["iy", "ix"]).agg(x=("x", "mean"), y=("y", "mean"), dep=("dep", "median"), n=("dep", "size")).reset_index()
print("@@ilerleme 0.3", flush=True)

nx = int(d["ix"].max()) + 3
ny = int(d["iy"].max()) + 3
xs = x0 + (np.arange(nx) + 0.5) * HUCRE
ys = y0 + (np.arange(ny) + 0.5) * HUCRE
GX, GY = np.meshgrid(xs, ys)
t = mtri.Triangulation(g["x"], g["y"])
p = np.c_[g["x"], g["y"]][t.triangles]
e = np.max([np.hypot(*(p[:, i] - p[:, (i + 1) % 3]).T) for i in range(3)], axis=0)
t.set_mask(e > MAX_KENAR)
Z = mtri.LinearTriInterpolator(t, g["dep"].to_numpy())(GX, GY).filled(np.nan)
N = np.zeros((ny, nx), np.int32)
N[g["iy"].to_numpy(), g["ix"].to_numpy()] = g["n"].to_numpy()
# satir 0 = kuzey olacak sekilde cevir
Z, N = Z[::-1], N[::-1]
np.savez_compressed(os.path.join(OUT, "derinlik_izgara.npz"), Z=Z.astype(np.float32), N=N,
                    x0=x0, y1=y0 + ny * HUCRE, hucre=HUCRE, epsg=crs.to_epsg())
print(f"Izgara {nx}x{ny} hucre, {np.isfinite(Z).sum()} dolu, EPSG:{crs.to_epsg()}")
print("@@ilerleme 1.0", flush=True)
