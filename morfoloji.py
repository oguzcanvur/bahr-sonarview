"""Dip morfolojisi, hacim, ses hizi duzeltmesi, kapsama ve yeni olcum rotasi.

Ciktilar (cozumleme/morfoloji):
  M1_egim_purzluluk.png   - dip egimi ve puruzlulugu (uydu uzerinde)
  M2_hacim.png            - tum golet icin tahmini derinlik ve hacim
  M3_kapsama_rota.png     - olculen / olculmeyen alanlar ve onerilen yeni rota
  yeni_rota.gpx           - Garmin'e yuklenecek rota
  morfoloji_ozet.csv      - sayisal ozet
Kullanim:  .venv\\Scripts\\python morfoloji.py   (once kontur.py, zemin.py, uydu.py)
"""
import math
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.tri as mtri
from uydu_altlik import Mozaik, merc, inv_merc, altlik

OUT = "cozumleme/morfoloji"
os.makedirs(OUT, exist_ok=True)
HAT_ARALIGI = 5.0       # yeni rotada hatlar arasi (m)
KIYI_PAYI = 3.0         # teknenin kiyiya yaklasabilecegi en yakin mesafe (m)
KAPSAMA_YARICAP = 2.5   # bir noktayi "olculmus" saymak icin rotaya en fazla uzaklik (m)
HIZ_KMSA = 2.5          # planlanan tarama hizi


def kaydet(fig, ad, dpi=130):
    yol = os.path.join(OUT, ad)
    if os.path.exists(yol):
        os.remove(yol)
    fig.tight_layout()
    fig.savefig(yol, dpi=dpi)
    plt.close(fig)
    print("->", yol)


def gauss_grid(Z, sig):
    """NaN'lari dikkate alan basit Gauss yumusatma (sig: hucre)."""
    r = int(3 * sig)
    x = np.arange(-r, r + 1)
    kk = np.exp(-x ** 2 / (2 * sig ** 2))
    kk /= kk.sum()
    V = np.nan_to_num(Z)
    Wt = np.isfinite(Z).astype(float)
    for ax_ in (0, 1):
        V = np.apply_along_axis(lambda s: np.convolve(s, kk, "same"), ax_, V)
        Wt = np.apply_along_axis(lambda s: np.convolve(s, kk, "same"), ax_, Wt)
    out = V / np.where(Wt > 1e-6, Wt, np.nan)
    out[~np.isfinite(Z)] = np.nan
    return out


# ------------------------------------------------------------------ veriler
bat = pd.read_csv("cozumleme/grafikler/batimetri_grid_1m.csv")
rota = pd.read_csv("cozumleme/grafikler/ping_ozet.csv", usecols=["lat", "lon", "inst_dep_m", "tempC"])
rota_d = rota[rota["inst_dep_m"].notna()]
lat0 = rota_d["lat"].mean()
k = 1 / math.cos(math.radians(lat0))                   # Mercator birimi / yer metresi
moz = Mozaik()
bat["mx"], bat["my"] = merc(bat["lat"], bat["lon"])
rmx, rmy = merc(rota_d["lat"].to_numpy(), rota_d["lon"].to_numpy())

su = moz.su_maskesi(bat["mx"], bat["my"])
px_m = moz.px / k                                      # bir pikselin yerdeki boyu (m)
golet_alan = su.sum() * px_m ** 2

# yer metresi cinsinden yerel koordinat (x: dogu, y: kuzey)
X0m, Y0m = rmx.min(), rmy.min()
def yerel(mx, my):
    return (np.asarray(mx) - X0m) / k, (np.asarray(my) - Y0m) / k

bat["x"], bat["y"] = yerel(bat["mx"], bat["my"])

# 1 m'lik duzenli grid (golet maskesi icinde)
rows, cols = np.nonzero(su)
gmx, gmy = moz.to_merc(cols, rows)
gx, gy = yerel(gmx, gmy)
xs = np.arange(np.floor(gx.min()), np.ceil(gx.max()) + 1, 1.0)
ys = np.arange(np.floor(gy.min()), np.ceil(gy.max()) + 1, 1.0)
GX, GY = np.meshgrid(xs, ys)
# grid hucresi gol icinde mi: maskeyi grid merkezinde ornekle
cc, rr = moz.to_px(GX * k + X0m, GY * k + Y0m)
inside = np.zeros(GX.shape, bool)
okp = (rr >= 0) & (rr < su.shape[0]) & (cc >= 0) & (cc < su.shape[1])
inside[okp] = su[rr[okp].astype(int), cc[okp].astype(int)]

# ------------------------------------------------------------------ 1) olculen alan: derinlik grid'i
tri = mtri.Triangulation(bat["x"], bat["y"])
p = np.c_[bat["x"], bat["y"]][tri.triangles]
e = np.max([np.hypot(*(p[:, i] - p[:, (i + 1) % 3]).T) for i in range(3)], axis=0)
tri.set_mask(e > 7.0)
D_olc = mtri.LinearTriInterpolator(tri, bat["derinlik_m"])(GX, GY).filled(np.nan)
D_olc[~inside] = np.nan
olculen_alan = np.isfinite(D_olc).sum()
olculen_hacim = np.nansum(D_olc)

# ------------------------------------------------------------------ 2) tum golet: kiyida D_kiyi varsayimiyla ara degerleme
# kiyi noktalari: maske kenari
kenar = su & ~moz.erode(su, 0.5, k)
kr, kc = np.nonzero(kenar)
kx, ky = yerel(*moz.to_merc(kc, kr))
sec = np.arange(0, kx.size, max(1, kx.size // 600))
kx, ky = kx[sec], ky[sec]


def tum_golet(d_kiyi):
    px_ = np.r_[bat["x"], kx]
    py_ = np.r_[bat["y"], ky]
    pz_ = np.r_[bat["derinlik_m"], np.full(kx.size, d_kiyi)]
    t = mtri.Triangulation(px_, py_)
    Z = mtri.LinearTriInterpolator(t, pz_)(GX, GY).filled(np.nan)
    Z[~inside] = np.nan
    Z = np.where(np.isfinite(D_olc), D_olc, Z)        # olculen yerde olcum
    return Z


D_tum0 = tum_golet(0.0)      # kiyida 0 m (yumusak kiyi)
D_tum5 = tum_golet(0.5)      # kiyida 0,5 m (dik sev / set)
hacim0, hacim5 = np.nansum(D_tum0), np.nansum(D_tum5)

# ------------------------------------------------------------------ 3) ses hizi duzeltmesi
T = float(rota_d["tempC"].median())
c_gercek = (1402.388 + 5.03711 * T - 0.0580852 * T ** 2 + 3.3420e-4 * T ** 3
            - 1.47800e-6 * T ** 4 + 3.1464e-9 * T ** 5)     # tatli su (Marczak 1997)
ses = pd.DataFrame({"cihazin_varsaydigi_m_s": [1463.0, 1500.0]})
ses["duzeltme_carpani"] = c_gercek / ses["cihazin_varsaydigi_m_s"]
ses["2.5m_icin_fark_cm"] = (2.5 * (ses["duzeltme_carpani"] - 1) * 100).round(1)

# ------------------------------------------------------------------ 4) egim ve puruzluluk
Ds = gauss_grid(D_olc, 1.5)
gyy, gxx = np.gradient(Ds, 1.0)
egim = np.degrees(np.arctan(np.hypot(gxx, gyy)))

zc = np.load("cozumleme/zemin/_ping_oznitelik_onbellek.npz")
meta = pd.read_csv("cozumleme/meta/B001_ds_hifreq_meta.csv")
has = meta["inst_dep_m"].notna()
seg = (has.astype(int).diff() != 0).cumsum()
meta = meta[has & (has.groupby(seg).transform("sum") >= 1000)].reset_index(drop=True)
meta["b"] = zc["bottom"]
hiz = meta["speed_ms"].where(meta["speed_ms"] < 5).rolling(51, center=True, min_periods=5).median()
meta["art"] = meta["b"] - meta["b"].rolling(101, center=True, min_periods=20).median()
mv = meta[(hiz >= 0.3) & meta["art"].notna()].copy()       # yavas anlar: tekne salinimi baskin
mv["x"], mv["y"] = yerel(*merc(mv["lat"], mv["lon"]))
mv["ix"] = np.round(mv["x"] - xs[0]).astype(int)
mv["iy"] = np.round(mv["y"] - ys[0]).astype(int)
pr = mv.groupby(["iy", "ix"])["art"].agg(lambda s: 1.4826 * np.median(np.abs(s - s.median())))
P = np.full(GX.shape, np.nan)
iy_, ix_ = zip(*pr.index)
P[np.array(iy_), np.array(ix_)] = pr.to_numpy() * 100        # cm
cnt = mv.groupby(["iy", "ix"]).size()
P[np.array(iy_)[cnt.to_numpy() < 10], np.array(ix_)[cnt.to_numpy() < 10]] = np.nan
P = gauss_grid(np.where(np.isfinite(D_olc), P, np.nan), 3.0)

# ------------------------------------------------------------------ 5) kapsama
ix_in, iy_in = GX[inside], GY[inside]
tx, ty = yerel(rmx[::5], rmy[::5])
dmin = np.full(ix_in.size, np.inf, np.float32)
for s in range(0, ix_in.size, 400):
    dd = np.hypot(ix_in[s:s + 400, None] - tx[None, :], iy_in[s:s + 400, None] - ty[None, :])
    dmin[s:s + 400] = dd.min(1)
KAP = np.full(GX.shape, np.nan)
KAP[inside] = dmin
kapsanan = (dmin <= KAPSAMA_YARICAP).sum()

# ------------------------------------------------------------------ 6) yeni rota: K-G hatlar, kiyidan KIYI_PAYI icerde
ic = moz.erode(su, KIYI_PAYI, k)
hatlar = []
for x in np.arange(xs[0] + KIYI_PAYI, xs[-1] - KIYI_PAYI + 0.01, HAT_ARALIGI):
    yy = np.arange(ys[0], ys[-1], 0.5)
    c_, r_ = moz.to_px(np.full(yy.size, x) * k + X0m, yy * k + Y0m)
    okk = (r_ >= 0) & (r_ < ic.shape[0]) & (c_ >= 0) & (c_ < ic.shape[1])
    icinde = np.zeros(yy.size, bool)
    icinde[okk] = ic[r_[okk].astype(int), c_[okk].astype(int)]
    # en uzun kesintisiz parca
    best, cur, bs = (0, 0), None, 0
    for j, f in enumerate(icinde):
        if f and cur is None:
            cur = j
        if (not f or j == yy.size - 1) and cur is not None:
            jj = j if f else j - 1
            if jj - cur > best[1] - best[0]:
                best = (cur, jj)
            cur = None
    if (best[1] - best[0]) * 0.5 >= 8:
        hatlar.append((x, yy[best[0]], yy[best[1]]))
# yilan seklinde sirala
wp = []
for i, (x, y0, y1) in enumerate(hatlar):
    seq = [(x, y0), (x, y1)] if i % 2 == 0 else [(x, y1), (x, y0)]
    wp += [(i + 1, a, b) for a, b in seq]
wp = pd.DataFrame(wp, columns=["hat", "x", "y"])
wlat, wlon = inv_merc(wp["x"] * k + X0m, wp["y"] * k + Y0m)
wp["lat"], wp["lon"] = wlat, wlon
hat_uz = sum(y1 - y0 for _, y0, y1 in hatlar)
gecis_uz = np.hypot(np.diff(wp["x"]), np.diff(wp["y"])).sum()
sure_dk = gecis_uz / (HIZ_KMSA / 3.6) / 60
pts = "\n".join(f'    <rtept lat="{a:.7f}" lon="{b:.7f}"><name>H{h:02d}{"A" if j % 2 == 0 else "B"}</name></rtept>'
                for j, (h, a, b) in enumerate(zip(wp["hat"], wp["lat"], wp["lon"])))
gpx = ('<?xml version="1.0" encoding="UTF-8"?>\n'
       '<gpx version="1.1" creator="morfoloji.py" xmlns="http://www.topografix.com/GPX/1/1">\n'
       f'  <rte>\n    <name>Golet tarama {HAT_ARALIGI:.0f}m</name>\n{pts}\n  </rte>\n</gpx>\n')
with open(os.path.join(OUT, "yeni_rota.gpx"), "w", encoding="utf-8") as f:
    f.write(gpx)
wp.to_csv(os.path.join(OUT, "yeni_rota_noktalari.csv"), index=False)

# ------------------------------------------------------------------ ozet
oz = {
    "golet_su_alani_m2": round(golet_alan),
    "olculen_alan_m2": int(olculen_alan),
    "olculen_alan_yuzde": round(100 * olculen_alan / inside.sum(), 1),
    "olculen_alan_hacmi_m3": round(olculen_hacim),
    "olculen_alan_ort_derinlik_m": round(olculen_hacim / olculen_alan, 2),
    "tum_golet_hacmi_m3_kiyi0m": round(hacim0),
    "tum_golet_hacmi_m3_kiyi0.5m": round(hacim5),
    "rota_2.5m_icinde_kalan_alan_yuzde": round(100 * kapsanan / inside.sum(), 1),
    "su_sicakligi_C": round(T, 1),
    "gercek_ses_hizi_m_s": round(c_gercek, 1),
    "egim_medyan_derece": round(float(np.nanmedian(egim)), 2),
    "egim_p95_derece": round(float(np.nanpercentile(egim, 95)), 2),
    "puruzluluk_medyan_cm": round(float(np.nanmedian(P)), 1),
    "yeni_rota_hat_sayisi": len(hatlar),
    "yeni_rota_uzunluk_m": round(gecis_uz),
    "yeni_rota_sure_dk": round(sure_dk),
}
pd.Series(oz).to_csv(os.path.join(OUT, "morfoloji_ozet.csv"), header=["deger"])
for a, b in oz.items():
    print(f"{a:38s} {b}")
print(ses.round(4).to_string(index=False))

# ------------------------------------------------------------------ gorseller
def m2v(Z):
    return Z


EXT_G = [xs[0] * k + X0m - 0.5 * k, xs[-1] * k + X0m + 0.5 * k, ys[0] * k + Y0m - 0.5 * k, ys[-1] * k + Y0m + 0.5 * k]
VIEW = [EXT_G[0] - 12 * k, EXT_G[1] + 12 * k, EXT_G[2] - 12 * k, EXT_G[3] + 12 * k]


def grid_goster(ax, Z, cmap, lv, alpha=0.75, label=""):
    im = ax.imshow(np.ma.masked_invalid(Z), extent=EXT_G, origin="lower", cmap=cmap,
                   vmin=lv[0], vmax=lv[1], alpha=alpha, interpolation="nearest")
    cb = plt.colorbar(im, ax=ax, shrink=0.6, label=label)
    return im


def kiyi_ciz(ax, color="white"):
    ax.contour(su.astype(float), [0.5], colors=color, linewidths=1.0, extent=moz.ext, origin="upper")


# M1 egim + puruzluluk
fig, axs = plt.subplots(1, 2, figsize=(17, 9.5))
altlik(axs[0], moz, VIEW, k, f"Dip egimi (derece)  - medyan {oz['egim_medyan_derece']}°, en dik %5: > {oz['egim_p95_derece']}°")
grid_goster(axs[0], egim, "magma_r", [0, np.nanpercentile(egim, 98)], label="egim (°)")
cs = axs[0].contour(GX * k + X0m, GY * k + Y0m, Ds, levels=[1.5, 2.0, 2.5, 3.0], colors="white", linewidths=0.6)
axs[0].clabel(cs, fmt="%.1f m", fontsize=7)
altlik(axs[1], moz, VIEW, k, "Dip puruzlulugu (dip cizgisinin 4 sn'lik ortalamadan sapmasi)")
grid_goster(axs[1], P, "cividis", [np.nanpercentile(P, 2), np.nanpercentile(P, 98)], label="puruzluluk (cm)")
for a in axs:
    kiyi_ciz(a)
kaydet(fig, "M1_egim_puruzluluk.png")

# M2 hacim
fig, ax = plt.subplots(figsize=(10, 11))
altlik(ax, moz, VIEW, k, "Tum golet icin tahmini derinlik (olculmeyen yerler kiyiya dogru ara degerlendi)")
grid_goster(ax, D_tum0, "viridis_r", [0, 3.2], alpha=0.8, label="derinlik (m)")
ax.contour(np.isfinite(D_olc).astype(float), [0.5], colors="yellow", linewidths=1.3, extent=EXT_G, origin="lower")
kiyi_ciz(ax)
ax.plot([], [], color="yellow", label="olculen alanin siniri")
ax.plot([], [], color="white", label="kiyi cizgisi (uydudan)")
ax.legend(loc="upper left", fontsize=9)
txt = (f"Golet su alani: {oz['golet_su_alani_m2']:,} m²\n"
       f"Olculen alan: {oz['olculen_alan_m2']:,} m² (%{oz['olculen_alan_yuzde']})\n"
       f"Olculen alanin hacmi: {oz['olculen_alan_hacmi_m3']:,} m³\n"
       f"Tum golet tahmini: {oz['tum_golet_hacmi_m3_kiyi0m']:,} – {oz['tum_golet_hacmi_m3_kiyi0.5m']:,} m³\n"
       f"(kiyida 0 m / 0,5 m derinlik varsayimi)").replace(",", ".")
ax.text(0.02, 0.10, txt, transform=ax.transAxes, fontsize=10, va="bottom",
        bbox=dict(boxstyle="round", fc="white", alpha=0.9))
kaydet(fig, "M2_hacim.png")

# M3 kapsama + yeni rota
fig, ax = plt.subplots(figsize=(10, 11))
altlik(ax, moz, VIEW, k, f"Kapsama ve onerilen yeni rota ({len(hatlar)} hat, {HAT_ARALIGI:.0f} m aralik, "
       f"~{oz['yeni_rota_uzunluk_m']} m, ~{oz['yeni_rota_sure_dk']} dk @ {HIZ_KMSA} km/sa)")
KAPc = np.where(KAP <= KAPSAMA_YARICAP, 1.0, np.where(np.isfinite(KAP), 0.0, np.nan))
ax.imshow(np.ma.masked_invalid(KAPc), extent=EXT_G, origin="lower", cmap=matplotlib.colors.ListedColormap(["#d7301f", "#31a354"]),
          vmin=0, vmax=1, alpha=0.45, interpolation="nearest")
kiyi_ciz(ax)
wmx, wmy = wp["x"] * k + X0m, wp["y"] * k + Y0m
ax.plot(wmx, wmy, color="yellow", lw=1.4, zorder=5)
for h, g in wp.assign(mx=wmx, my=wmy).groupby("hat"):
    ax.annotate(str(h), (g["mx"].iloc[0], g["my"].iloc[0]), fontsize=8, color="black", ha="center",
                bbox=dict(boxstyle="circle,pad=0.15", fc="yellow", ec="none"), zorder=6)
ax.plot(wmx.iloc[0], wmy.iloc[0], marker="o", ms=10, mfc="lime", mec="k", zorder=7)
ax.fill([], [], color="#31a354", alpha=0.6, label=f"olculmus (rotaya ≤ {KAPSAMA_YARICAP} m): %{oz['rota_2.5m_icinde_kalan_alan_yuzde']}")
ax.fill([], [], color="#d7301f", alpha=0.6, label="olculmemis")
ax.plot([], [], color="yellow", lw=1.4, label="onerilen rota (yesil nokta: baslangic)")
ax.legend(loc="upper left", fontsize=9)
kaydet(fig, "M3_kapsama_rota.png")
