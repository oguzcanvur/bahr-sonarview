"""Batimetri, zemin siniflari ve numune noktalarini uydu goruntusu uzerine bindirir.

Uydu altligi: Esri World Imagery (karolar internetten indirilir, cozumleme/uydu/_karolar altinda saklanir).
Kullanim:  .venv\\Scripts\\python uydu.py      (once kontur.py, zemin.py, numune.py calismis olmali)
"""
import io
import math
import os
import urllib.request
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.tri as mtri
from matplotlib.colors import ListedColormap
from PIL import Image

OUT = "cozumleme/uydu"
CACHE = os.path.join(OUT, "_karolar")
ZOOM = 19
PAY = 25.0          # veri alaninin cevresine eklenecek bosluk (m)
MAX_EDGE = 7.0      # (m) bundan uzun ucgen = veri yok
URL = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
KAYNAK = "Uydu: Esri World Imagery (Esri, Maxar, Earthstar Geographics)"
os.makedirs(CACHE, exist_ok=True)
R = 6378137.0


def merc(lat, lon):
    lat, lon = np.asarray(lat, float), np.asarray(lon, float)
    return R * np.radians(lon), R * np.log(np.tan(np.pi / 4 + np.radians(lat) / 2))


def tile_xy(lat, lon, z):
    n = 2 ** z
    return ((lon + 180) / 360 * n,
            (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n)


def tile_bounds_merc(x, y, z):
    size = 2 * math.pi * R / 2 ** z
    x0 = -math.pi * R + x * size
    y1 = math.pi * R - y * size
    return x0, x0 + size, y1 - size, y1


def get_tile(x, y, z):
    fn = os.path.join(CACHE, f"{z}_{x}_{y}.jpg")
    if not os.path.exists(fn):
        req = urllib.request.Request(URL.format(z=z, x=x, y=y), headers={"User-Agent": "sonar-analiz/1.0"})
        with urllib.request.urlopen(req, timeout=30) as r, open(fn, "wb") as f:
            f.write(r.read())
    return Image.open(fn).convert("RGB")


# ------------------------------------------------------------------ veriler
bat = pd.read_csv("cozumleme/grafikler/batimetri_grid_1m.csv")
ZEMIN_VAR = os.path.exists("cozumleme/zemin/zemin_grid_1m.csv") and os.path.exists("cozumleme/zemin/numune_noktalari.csv")
zem = pd.read_csv("cozumleme/zemin/zemin_grid_1m.csv") if ZEMIN_VAR else None
if ZEMIN_VAR:
    zem = zem[zem["sinif"] >= 0]
num = pd.read_csv("cozumleme/zemin/numune_noktalari.csv") if ZEMIN_VAR else None
rota = pd.read_csv("cozumleme/grafikler/ping_ozet.csv", usecols=["lat", "lon", "inst_dep_m"]).iloc[::20]
rota = rota[rota["inst_dep_m"].notna()]

k = 1 / math.cos(math.radians(rota["lat"].mean()))   # Mercator olcek katsayisi (1 m yerde = k birim)
for df in [x for x in (bat, zem, num, rota) if x is not None]:
    lat = df["enlem"] if "enlem" in df else df["lat"]
    lon = df["boylam"] if "boylam" in df else df["lon"]
    df["mx"], df["my"] = merc(lat, lon)

# ------------------------------------------------------------------ uydu mozaigi
from uydu_altlik import Mozaik, kontur_seviyeleri
_moz = Mozaik()
EXT, IMG, ZOOM = _moz.ext, _moz.A, _moz.zoom

pad = PAY * k
VIEW = [rota["mx"].min() - pad, rota["mx"].max() + pad, rota["my"].min() - pad, rota["my"].max() + pad]


def masked_tri(df):
    t = mtri.Triangulation(df["mx"], df["my"])
    p = np.c_[df["mx"], df["my"]][t.triangles]
    e = np.max([np.hypot(*(p[:, i] - p[:, (i + 1) % 3]).T) for i in range(3)], axis=0)
    t.set_mask(e > MAX_EDGE * k)
    return t


def base(ax, title):
    ax.imshow(IMG, extent=EXT, origin="upper", interpolation="bilinear")
    ax.set_xlim(VIEW[:2]); ax.set_ylim(VIEW[2:])
    ax.set_aspect("equal")
    ax.set_xticks([]); ax.set_yticks([])
    ax.set_title(title, fontsize=12)
    # olcek cubugu (20 m) + kuzey oku
    x0 = VIEW[0] + 0.05 * (VIEW[1] - VIEW[0]); y0 = VIEW[2] + 0.04 * (VIEW[3] - VIEW[2])
    ax.plot([x0, x0 + 20 * k], [y0, y0], color="white", lw=4, solid_capstyle="butt")
    ax.plot([x0, x0 + 20 * k], [y0, y0], color="black", lw=1.5, solid_capstyle="butt")
    ax.text(x0 + 10 * k, y0 + 2.5 * k, "20 m", color="white", ha="center", fontsize=10, weight="bold")
    xn, yn = VIEW[1] - 0.06 * (VIEW[1] - VIEW[0]), VIEW[3] - 0.12 * (VIEW[3] - VIEW[2])
    ax.annotate("K", xy=(xn, yn + 12 * k), xytext=(xn, yn), color="white", ha="center", fontsize=13, weight="bold",
                arrowprops=dict(arrowstyle="-|>", color="white", lw=2))
    ax.text(0.99, 0.005, KAYNAK, transform=ax.transAxes, ha="right", va="bottom", fontsize=7, color="white")


def kaydet(fig, ad):
    yol = os.path.join(OUT, ad)
    if os.path.exists(yol):
        os.remove(yol)
    fig.tight_layout()
    fig.savefig(yol, dpi=140)
    plt.close(fig)
    print("->", yol)


# 0) sadece uydu + rota
fig, ax = plt.subplots(figsize=(10, 11))
base(ax, "Uydu goruntusu ve tekne rotasi")
ax.plot(rota["mx"], rota["my"], color="yellow", lw=0.6, alpha=0.9)
kaydet(fig, "U0_uydu_rota.png")

# 1) batimetri
fig, ax = plt.subplots(figsize=(10, 11))
base(ax, "Derinlik haritasi (batimetri)")
t = masked_tri(bat)
lv = np.arange(np.floor(bat["derinlik_m"].min() * 4) / 4, bat["derinlik_m"].max() + 0.25, 0.25)
cf = ax.tricontourf(t, bat["derinlik_m"], levels=lv, cmap="viridis_r", alpha=0.7)
cs = ax.tricontour(t, bat["derinlik_m"], levels=kontur_seviyeleri(bat["derinlik_m"]), colors="white", linewidths=0.9)
ax.clabel(cs, fmt="%.1f m", fontsize=9, colors="white")
plt.colorbar(cf, ax=ax, shrink=0.6, label="Derinlik (m)")
kaydet(fig, "U1_uydu_batimetri.png")

# 2) zemin siniflari + numune noktalari
if not ZEMIN_VAR:
    raise SystemExit(0)
COLS = ["#8c510a", "#dfc27d", "#35978f"]
ISIM = ["Yumuşak çamur birikintisi", "Orta: silt / ince çamur", "Daha sıkı / sert zemin"]
fig, ax = plt.subplots(figsize=(10, 11))
base(ax, "Akustik zemin siniflari ve numune noktalari")
t = masked_tri(zem)
ax.tricontourf(t, zem["sinif"].astype(float), levels=np.arange(-0.5, 3), cmap=ListedColormap(COLS), alpha=0.65)
for r in num.itertuples():
    ax.add_patch(plt.Circle((r.mx, r.my), 5 * k, fill=False, ls="--", lw=1, color="white"))
    ax.plot(r.mx, r.my, marker="*", ms=18, mfc="red", mec="white")
    ax.annotate(r.nokta, (r.mx, r.my), xytext=(7, 7), textcoords="offset points", fontsize=10, weight="bold",
                bbox=dict(boxstyle="round,pad=0.2", fc="white", alpha=0.85))
for i in range(3):
    ax.scatter([], [], c=COLS[i], marker="s", s=80, label=ISIM[i])
ax.plot([], [], "r*", ms=14, mec="white", label="Numune noktasi (daire: 5 m)")
ax.legend(loc="upper left", fontsize=9, framealpha=0.9)
kaydet(fig, "U2_uydu_zemin_numune.png")
