"""Iki tarihteki taramanin karsilastirilmasi: dip kotu degisimi, sediman birikimi / oyulma, yillik hiz.

Karsilastirilan proje: parametreler 'degisim_proje' (ayni Projeler klasorunde).
Dip kotu = su yuzeyi kotu - derinlik. Iki projede su yuzeyi kotu ayni referansta girilmelidir;
girilmediyse (ikisi de 0) su seviyelerinin ayni oldugu kabul edilir.
|degisim| < ESIK (olcum belirsizligi) olan hucreler "anlamli degil" sayilir.
Ciktilar: cozumleme/degisim/ G1_degisim_haritasi.png, degisim_izgara.csv ; cozumleme/web/degisim.json, katman_degisim.json
"""
import json
import os
import sys
from datetime import date

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from pyproj import CRS, Transformer  # noqa: E402

from katmanlar import raster, yaz  # noqa: E402
from ortak import kaydet_png, parametreler  # noqa: E402

ESIK = 0.10
P = parametreler()
OUT = "cozumleme/degisim"
os.makedirs(OUT, exist_ok=True)
diger = str(P.get("degisim_proje") or "").strip()
if not diger:
    sys.exit("HATA: Karşılaştırılacak proje seçilmedi.")
dk = os.path.join("..", diger)
if os.path.abspath(dk) == os.path.abspath("."):
    sys.exit("HATA: Proje kendisiyle karşılaştırılamaz.")
if not os.path.exists(os.path.join(dk, "cozumleme/grafikler/derinlik_izgara.npz")):
    sys.exit("HATA: Seçilen projede derinlik ızgarası yok. O projede temel analizi (bu sürümle) yeniden çalıştırın.")


def oku(yol):
    try:
        with open(yol, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def proje_bilgi(kok):
    pj = oku(os.path.join(kok, "proje.json"))
    oz = oku(os.path.join(kok, "cozumleme/web/ozet.json"))
    par = oku(os.path.join(kok, "parametreler.json"))
    su = par.get("su_kotu", (pj.get("parametreler") or {}).get("su_kotu", 0.0)) or 0.0
    return {"ad": pj.get("ad", kok), "tarih": oz.get("tarih", ""), "su_kotu": float(su)}


bu = proje_bilgi(".")
bu["su_kotu"] = float(P.get("su_kotu") or 0.0)
ot = proje_bilgi(dk)
A = np.load("cozumleme/grafikler/derinlik_izgara.npz")
B = np.load(os.path.join(dk, "cozumleme/grafikler/derinlik_izgara.npz"))
ZA, x0, y1, h = A["Z"].astype(float), float(A["x0"]), float(A["y1"]), float(A["hucre"])
ny, nx = ZA.shape
GX, GY = np.meshgrid(x0 + (np.arange(nx) + 0.5) * h, y1 - (np.arange(ny) + 0.5) * h)
crsA, crsB = CRS.from_epsg(int(A["epsg"])), CRS.from_epsg(int(B["epsg"]))
bx, by = (GX, GY) if crsA == crsB else Transformer.from_crs(crsA, crsB, always_xy=True).transform(GX, GY)
ZB_ = B["Z"].astype(float)
cb = np.floor((bx - float(B["x0"])) / float(B["hucre"])).astype(int)
rb = np.floor((float(B["y1"]) - by) / float(B["hucre"])).astype(int)
ok = (cb >= 0) & (cb < ZB_.shape[1]) & (rb >= 0) & (rb < ZB_.shape[0])
ZB = np.full_like(ZA, np.nan)
ZB[ok] = ZB_[rb[ok], cb[ok]]

# hangisi eski?
def gun(s):
    try:
        return date.fromisoformat(str(s)[:10])
    except Exception:
        return None


ta, tb = gun(bu["tarih"]), gun(ot["tarih"])
if ta and tb and ta < tb:
    eski, yeni, Ze, Zy = bu, ot, ZA, ZB
else:
    eski, yeni, Ze, Zy = ot, bu, ZB, ZA
yil = ((gun(yeni["tarih"]) - gun(eski["tarih"])).days / 365.25) if (ta and tb) else None
# yalnizca birinde su yuzeyi kotu girildiyse referanslar uyusmaz: ikisini de ayni seviye kabul et
tek_kot = (eski["su_kotu"] == 0) != (yeni["su_kotu"] == 0)
if tek_kot:
    eski = dict(eski, su_kotu=0.0)
    yeni = dict(yeni, su_kotu=0.0)
# dip kotu degisimi: + birikim (dip yukseldi), - oyulma (dip derinlesti)
dE = (yeni["su_kotu"] - Zy) - (eski["su_kotu"] - Ze)
ortak = np.isfinite(dE)
if ortak.sum() < 20:
    sys.exit("HATA: İki taramanın ortak ölçülen alanı çok küçük; aynı gölete ait olduklarından emin olun.")
anlamli = ortak & (np.abs(dE) >= ESIK)
alan = h * h
birikim = float(dE[anlamli & (dE > 0)].sum() * alan)
oyulma = float(abs(dE[anlamli & (dE < 0)].sum()) * alan)
net = float(np.nansum(dE[ortak]) * alan)
sonuc = {
    "eski": eski, "yeni": yeni, "yil": None if yil is None else round(yil, 2),
    "ortak_alan_m2": round(float(ortak.sum() * alan)), "esik_m": ESIK,
    "ortalama_degisim_cm": round(float(np.nanmean(dE[ortak]) * 100), 1),
    "birikim_alani_m2": round(float((anlamli & (dE > 0)).sum() * alan)),
    "oyulma_alani_m2": round(float((anlamli & (dE < 0)).sum() * alan)),
    "birikim_m3": round(birikim), "oyulma_m3": round(oyulma), "net_m3": round(net),
    "yillik_net_m3": None if not yil else round(net / yil), "yillik_cm": None if not yil else round(float(np.nanmean(dE[ortak]) * 100) / yil, 1),
    "su_seviyesi_uyari": (eski["su_kotu"] == 0 and yeni["su_kotu"] == 0) or tek_kot, "tek_kot": tek_kot,
}
yaz("degisim.json", sonuc)

r, c = np.nonzero(ortak)
lon, lat = Transformer.from_crs(crsA, 4326, always_xy=True).transform(GX[r, c], GY[r, c])
pd.DataFrame({"lat": lat, "lon": lon, "eski_derinlik_m": Ze[r, c], "yeni_derinlik_m": Zy[r, c], "dip_kotu_degisimi_m": dE[r, c]}
             ).round(4).to_csv(os.path.join(OUT, "degisim_izgara.csv"), index=False)
lim = float(max(0.2, np.nanpercentile(np.abs(dE[ortak]), 97)))
k = raster(lat, lon, dE[r, c], "degisim.png", "RdBu_r", -lim, lim, alpha=0.8)
k.update({"min": -round(lim, 2), "max": round(lim, 2)})
yaz("katman_degisim.json", k)

fig, axs = plt.subplots(1, 2, figsize=(15, 7), gridspec_kw={"width_ratios": [1.3, 1]})
D = np.where(ortak, dE, np.nan) * 100
im = axs[0].imshow(D, cmap="RdBu_r", vmin=-lim * 100, vmax=lim * 100, extent=[0, nx * h, 0, ny * h], interpolation="nearest")
fig.colorbar(im, ax=axs[0], label="dip kotu değişimi (cm)  + birikim / − oyulma")
axs[0].set_title(f"{eski['tarih']} → {yeni['tarih']}" + (f"  ({yil:.1f} yıl)" if yil else ""))
axs[0].set_xlabel("Doğu (m)"); axs[0].set_ylabel("Kuzey (m)")
axs[1].hist(dE[ortak] * 100, bins=50, color="#64748b")
axs[1].axvspan(-ESIK * 100, ESIK * 100, color="#fbbf24", alpha=0.25, label=f"±{ESIK * 100:.0f} cm: anlamlı değil")
axs[1].set_xlabel("dip kotu değişimi (cm)"); axs[1].set_ylabel("hücre sayısı"); axs[1].legend()
axs[1].set_title(f"Birikim {birikim:,.0f} m³ · oyulma {oyulma:,.0f} m³ · net {net:+,.0f} m³".replace(",", "."))
fig.tight_layout()
kaydet_png(fig, os.path.join(OUT, "G1_degisim_haritasi.png"))
plt.close(fig)
print(json.dumps(sonuc, ensure_ascii=False))
print("@@ilerleme 1.0")
