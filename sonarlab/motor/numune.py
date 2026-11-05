"""Her akustik zemin sinifindan dip numunesi alinacak temsili noktalari secer.

Secim olcutleri (her hucre icin):
  - Sinifin "tipik" ornegi olmali: oznitelikleri sinif merkezine yakin
  - Sinif sinirindan uzak olmali (GPS hatasi / ~10 m yumusatma payi)
  - Yeterince ping'le olculmus olmali
  - Ayni siniftaki noktalar birbirinden en az MIN_ARA metre uzak olmali

Cikti: CSV (tablo), GPX (Garmin cihaza yuklemek icin), PNG (harita).
Kullanim:  .venv\\Scripts\\python numune.py      (once zemin.py calismis olmali)
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.tri as mtri
from matplotlib.colors import ListedColormap
from uydu_altlik import kontur_seviyeleri

OUT = "cozumleme/zemin"
NOKTA_SAYISI = {0: 3, 1: 3, 2: 2}   # sinif -> kac nokta
MIN_ARA = 12.0                      # ayni siniftaki noktalar arasi min. mesafe (m)
MIN_PING = 15
ISIM = {0: "Yumuşak çamur birikintisi", 1: "Orta: silt / ince çamur", 2: "Daha sıkı / sert zemin"}
KISA = {0: "CAMUR", 1: "SILT", 2: "SERT"}
COLS = ["#8c510a", "#dfc27d", "#35978f"]

g = pd.read_csv(os.path.join(OUT, "zemin_grid_1m.csv"))
g = g[g["sinif"] >= 0].reset_index(drop=True)
F = ["peak", "contrast", "decay_res"]
Z = (g[F] - g[F].median()) / (g[F].quantile(.75) - g[F].quantile(.25))

P = g[["x", "y"]].to_numpy()
D = np.hypot(*(P[:, None, :] - P[None, :, :]).transpose(2, 0, 1))
lab = g["sinif"].to_numpy()

# sinira uzaklik: farkli siniftaki en yakin hucre (yoksa 15 m ile sinirla)
other = lab[:, None] != lab[None, :]
g["sinira_m"] = np.where(other.any(1), np.where(other, D, np.inf).min(1), 15.0).clip(max=15.0)
# kapsama: 5 m yaricapli dairenin ne kadari olculmus (taranan alanin kenarindaki noktalari ele)
g["kapsama"] = ((D <= 5.0).sum(1) / (np.pi * 25)).clip(max=1.0)
# sinif merkezine (standart oznitelik uzayinda) uzaklik
cent = Z.groupby(lab).mean()
g["tipiklik"] = -np.sqrt(((Z.to_numpy() - cent.loc[lab].to_numpy()) ** 2).sum(1))

secim = []
for k, adet in NOKTA_SAYISI.items():
    c = g[(g["sinif"] == k) & (g["n"] >= MIN_PING)].copy()
    if c.empty:
        continue
    # skor: sinirdan uzaklik (0-1) + tipiklik (0-1) + kapsama (0-1)
    c["skor"] = (c["sinira_m"] / 15.0
                 + (c["tipiklik"] - c["tipiklik"].min()) / (np.ptp(c["tipiklik"]) + 1e-9)
                 + c["kapsama"])
    c = c.sort_values("skor", ascending=False)
    # buyuk siniflarda noktalari alana yay: aralik = sinif alaninin kokuyle orantili
    ara = max(MIN_ARA, 1.0 * np.sqrt(len(c) / adet))
    alinan = []
    for i, r in c.iterrows():
        if all(np.hypot(r.x - g.loc[j, "x"], r.y - g.loc[j, "y"]) >= ara for j in alinan):
            alinan.append(i)
        if len(alinan) == adet:
            break
    secim += alinan

s = g.loc[secim].copy()
s["no"] = [f"{KISA[k]}-{i + 1}" for k, grp in s.groupby("sinif", sort=False) for i in range(len(grp))]
s["sinif_adi"] = s["sinif"].map(ISIM)
s = s.sort_values(["sinif", "no"])

tablo = pd.DataFrame({
    "nokta": s["no"],
    "sinif": s["sinif"],
    "beklenen_zemin": s["sinif_adi"],
    "enlem": s["lat"].round(6),
    "boylam": s["lon"].round(6),
    "derinlik_m": s["dep"].round(2),
    "sinira_uzaklik_m": s["sinira_m"].round(1),
    "kapsama_yuzde": (100 * s["kapsama"]).round(0),
    "ping_sayisi": s["n"],
    "numune_notu": "",
})
tablo.to_csv(os.path.join(OUT, "numune_noktalari.csv"), index=False, encoding="utf-8-sig")

# ---------------- GPX (Garmin: SD kartta /Garmin/GPX/ klasorune kopyalanir)
wpt = "\n".join(
    f'  <wpt lat="{r.enlem:.6f}" lon="{r.boylam:.6f}">\n'
    f"    <name>{r.nokta}</name>\n"
    f"    <desc>{r.beklenen_zemin}, derinlik {r.derinlik_m:.1f} m</desc>\n"
    f"    <sym>Flag, Blue</sym>\n"
    f"  </wpt>"
    for r in tablo.itertuples())
gpx = ('<?xml version="1.0" encoding="UTF-8"?>\n'
       '<gpx version="1.1" creator="numune.py" xmlns="http://www.topografix.com/GPX/1/1">\n'
       f"{wpt}\n</gpx>\n")
with open(os.path.join(OUT, "numune_noktalari.gpx"), "w", encoding="utf-8") as f:
    f.write(gpx)

# ---------------- harita
tri = mtri.Triangulation(g["x"], g["y"])
p = P[tri.triangles]
edges = np.max([np.hypot(*(p[:, i] - p[:, (i + 1) % 3]).T) for i in range(3)], axis=0)
tri.set_mask(edges > 7.0)
fig, ax = plt.subplots(figsize=(11, 12))
ax.tricontourf(tri, g["sinif"].astype(float), levels=np.arange(-0.5, 3), cmap=ListedColormap(COLS), alpha=0.85)
cs = ax.tricontour(tri, g["dep"], levels=kontur_seviyeleri(g["dep"]), colors="k", linewidths=0.5, alpha=0.6)
ax.clabel(cs, fmt="%.1f m", fontsize=7)
for r in s.itertuples():
    ax.add_patch(plt.Circle((r.x, r.y), 5, fill=False, ls="--", lw=0.8, color="k"))
    ax.plot(r.x, r.y, marker="*", ms=20, mfc="red", mec="k")
    ax.annotate(r.no, (r.x, r.y), xytext=(7, 7), textcoords="offset points", fontsize=11, weight="bold",
                bbox=dict(boxstyle="round,pad=0.2", fc="white", alpha=0.85))
for k in range(3):
    ax.scatter([], [], c=COLS[k], marker="s", s=80, label=f"Sinif {k}: {ISIM[k]}")
ax.plot([], [], "r*", ms=14, mec="k", label="Numune noktasi (kesikli daire: 5 m tolerans)")
ax.legend(loc="lower left", fontsize=9, framealpha=0.9)
ax.set_aspect("equal")
ax.set_xlabel("Dogu (m)"); ax.set_ylabel("Kuzey (m)")
ax.set_title("Dip numunesi alinacak noktalar")
fig.tight_layout()
png = os.path.join(OUT, "9_numune_noktalari.png")
if os.path.exists(png):
    os.remove(png)   # Windows'ta mevcut PNG uzerine yazma bazen Errno 22 veriyor
fig.savefig(png, dpi=130)
plt.close(fig)

print(tablo.drop(columns=["numune_notu"]).to_string(index=False))
