"""Saha dogrulama verisiyle karsilastirma ve kalibrasyon onerisi.

Girdi: dogrulama.csv (proje klasoru) - sutunlar (Turkce ya da Ingilizce):
  nokta | enlem/lat | boylam/lon   (ya da x / y: secili koordinat sisteminde)
  derinlik_m / depth_m (istege bagli: cubuk ya da iskandil ile olculen su derinligi)
  zemin / substrate    (istege bagli: numunede gorulen zemin, or. camur, kum, cakil)

Derinlik: sonar izgarasindaki deger ile saha olcumu karsilastirilir (en yakin olcume <= 3 m olan noktalar).
  sonar = a * saha + b  dogrusu; sabit fark -> batma payi onerisi, egim -> ses hizi onerisi.
Zemin: noktadaki sonar sinifi ile numune karsilastirilir; her sinifa cogunluk numune adi onerilir.
Ciktilar: cozumleme/dogrulama/ D1_derinlik_dogrulama.png, dogrulama_sonuclari.csv ; cozumleme/web/dogrulama.json
"""
import json
import os
import sys

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from pyproj import CRS, Transformer  # noqa: E402

from ortak import kaydet_png, koordinat_sistemi, parametreler  # noqa: E402

P = parametreler()
OUT = "cozumleme/dogrulama"
os.makedirs(OUT, exist_ok=True)
if not os.path.exists("dogrulama.csv"):
    sys.exit("HATA: Doğrulama verisi yüklenmemiş. Önce şablona göre hazırlanmış CSV dosyasını yükleyin.")

ham = None
for sep in (",", ";", "\t"):
    for enc in ("utf-8-sig", "cp1254", "latin-1"):
        try:
            t = pd.read_csv("dogrulama.csv", sep=sep, encoding=enc)
            if t.shape[1] >= 3:
                ham = t
                break
        except Exception:
            continue
    if ham is not None:
        break
if ham is None:
    sys.exit("HATA: Doğrulama dosyası okunamadı. Virgül ya da noktalı virgülle ayrılmış CSV olmalı.")
ham.columns = [str(c).strip().lower() for c in ham.columns]
es = {"lat": "enlem", "latitude": "enlem", "lon": "boylam", "lng": "boylam", "longitude": "boylam",
      "depth_m": "derinlik_m", "depth": "derinlik_m", "derinlik": "derinlik_m", "substrate": "zemin", "sediment": "zemin",
      "point": "nokta", "name": "nokta", "id": "nokta"}
ham = ham.rename(columns={k: v for k, v in es.items() if k in ham.columns})
for c in ("enlem", "boylam", "x", "y", "derinlik_m"):
    if c in ham and not pd.api.types.is_numeric_dtype(ham[c]):
        ham[c] = pd.to_numeric(ham[c].astype(str).str.replace(",", ".", regex=False), errors="coerce")
if "nokta" not in ham:
    ham["nokta"] = [f"D{i + 1}" for i in range(len(ham))]

npz = np.load("cozumleme/grafikler/derinlik_izgara.npz")
Z, N = npz["Z"].astype(float), npz["N"]
x0, y1, h = float(npz["x0"]), float(npz["y1"]), float(npz["hucre"])
crs = CRS.from_epsg(int(npz["epsg"]))
if "enlem" in ham and "boylam" in ham:
    ux, uy = Transformer.from_crs(4326, crs, always_xy=True).transform(ham["boylam"].to_numpy(float), ham["enlem"].to_numpy(float))
elif "x" in ham and "y" in ham:
    oz = json.load(open("cozumleme/web/ozet.json", encoding="utf-8"))
    kc, _, _ = koordinat_sistemi(P.get("koordinat"), oz["merkez"][1])
    ux, uy = Transformer.from_crs(kc, crs, always_xy=True).transform(ham["x"].to_numpy(float), ham["y"].to_numpy(float))
else:
    sys.exit("HATA: Dosyada konum sütunları yok (enlem + boylam ya da x + y).")
ham["ux"], ham["uy"] = ux, uy
ny, nx = Z.shape
c = np.floor((ux - x0) / h).astype(int)
r = np.floor((y1 - uy) / h).astype(int)
ici = (c >= 0) & (c < nx) & (r >= 0) & (r < ny)
ham["sonar_m"] = np.nan
ham.loc[ici, "sonar_m"] = Z[r[ici], c[ici]]
# en yakin olculmus hucreye uzaklik
rr, cc = np.nonzero(N > 0)
mx, my = x0 + (cc + 0.5) * h, y1 - (rr + 0.5) * h
ham["olcume_uzaklik_m"] = [float(np.min(np.hypot(mx - a, my - b))) for a, b in zip(ux, uy)]

sonuc = {"nokta_sayisi": int(len(ham))}
# ---------------------------------------------------------------- derinlik
if "derinlik_m" in ham and ham["derinlik_m"].notna().any():
    d = ham[ham["derinlik_m"].notna() & ham["sonar_m"].notna() & (ham["olcume_uzaklik_m"] <= 3.0)].copy()
    d["fark_m"] = d["sonar_m"] - d["derinlik_m"]
    ham.loc[d.index, "fark_m"] = d["fark_m"]
    if len(d) >= 2:
        a, b = (np.polyfit(d["derinlik_m"], d["sonar_m"], 1) if len(d) >= 4 and d["derinlik_m"].std() > 0.2 else (1.0, float(d["fark_m"].mean())))
        bias = float(d["fark_m"].mean())
        rmse = float(np.sqrt((d["fark_m"] ** 2).mean()))
        oneri = {"batma_payi": round(float(P.get("batma_payi") or 0) - bias, 2)}
        # egim ancak istatistiksel olarak anlamliysa (|a-1| > 2 standart hata) ses hizi onerilir
        se = np.inf
        if len(d) >= 6:
            art = d["sonar_m"] - (a * d["derinlik_m"] + b)
            sxx = float(((d["derinlik_m"] - d["derinlik_m"].mean()) ** 2).sum())
            se = float(np.sqrt((art ** 2).sum() / (len(d) - 2)) / np.sqrt(sxx)) if sxx > 0 else np.inf
        if abs(a - 1) > max(0.03, 2 * se) and len(d) >= 6:
            oneri = {"batma_payi": round(float(P.get("batma_payi") or 0) - b, 2),
                     "ses_hizi_modu": "elle", "ses_hizi_elle": round(float(P.get("cihaz_ses_hizi") or 1500) / a, 0)}
        sonuc["derinlik"] = {"kullanilan": int(len(d)), "dislanan": int(ham["derinlik_m"].notna().sum() - len(d)),
                             "ortalama_fark_m": round(bias, 3), "std_m": round(float(d["fark_m"].std(ddof=1)) if len(d) > 2 else 0.0, 3),
                             "rmse_m": round(rmse, 3), "max_mutlak_m": round(float(d["fark_m"].abs().max()), 3),
                             "egim": round(float(a), 4), "kesisim_m": round(float(b), 3), "oneri": oneri}
        fig, axs = plt.subplots(1, 2, figsize=(14, 6))
        lim = [0, float(max(d["derinlik_m"].max(), d["sonar_m"].max()) * 1.1)]
        axs[0].scatter(d["derinlik_m"], d["sonar_m"], c="#0e7490", s=40, zorder=3)
        for _, q in d.iterrows():
            axs[0].annotate(str(q["nokta"]), (q["derinlik_m"], q["sonar_m"]), fontsize=8, xytext=(4, 4), textcoords="offset points")
        axs[0].plot(lim, lim, "k--", lw=1, label="1:1")
        xx = np.array(lim)
        axs[0].plot(xx, a * xx + b, color="#b45309", lw=1.5, label=f"sonar = {a:.3f}·saha {b:+.3f}")
        axs[0].set_xlim(lim); axs[0].set_ylim(lim); axs[0].set_aspect("equal")
        axs[0].set_xlabel("Saha ölçümü (m)"); axs[0].set_ylabel("Sonar (m)"); axs[0].legend(); axs[0].grid(alpha=0.3)
        axs[0].set_title(f"Derinlik doğrulaması — RMSE {rmse * 100:.1f} cm, ortalama fark {bias * 100:+.1f} cm")
        axs[1].bar(d["nokta"].astype(str), d["fark_m"] * 100, color=np.where(d["fark_m"] > 0, "#dc2626", "#2563eb"))
        axs[1].axhline(0, color="k", lw=0.8)
        axs[1].set_ylabel("Sonar − saha (cm)"); axs[1].set_title("Nokta bazında fark"); axs[1].tick_params(axis="x", rotation=60)
        fig.tight_layout()
        kaydet_png(fig, os.path.join(OUT, "D1_derinlik_dogrulama.png"))
        plt.close(fig)
    else:
        sonuc["derinlik"] = {"kullanilan": int(len(d)), "uyari": "Ölçüm hattına 3 m'den yakın en az 2 derinlik noktası gerekli"}

# ---------------------------------------------------------------- zemin
ZG = "cozumleme/zemin/zemin_grid_1m.csv"
if "zemin" in ham and ham["zemin"].notna().any() and os.path.exists(ZG):
    zg = pd.read_csv(ZG)
    zg = zg[zg["sinif"] >= 0]
    zx, zy = Transformer.from_crs(4326, crs, always_xy=True).transform(zg["lon"].to_numpy(), zg["lat"].to_numpy())
    snf = []
    for a, b in zip(ux, uy):
        dd = np.hypot(zx - a, zy - b)
        i = int(np.argmin(dd))
        snf.append(int(zg["sinif"].iloc[i]) if dd[i] <= 3.0 else -1)
    ham["sonar_sinif"] = snf
    z = ham[ham["zemin"].notna() & (ham["sonar_sinif"] >= 0)].copy()
    z["zemin"] = z["zemin"].astype(str).str.strip().str.lower()
    adlar = {}
    so = "cozumleme/zemin/zemin_sinif_ozeti.csv"
    if os.path.exists(so):
        adlar = {int(q["sinif"]): str(q["yorum"]) for _, q in pd.read_csv(so).iterrows()}
    tablo = pd.crosstab(z["sonar_sinif"], z["zemin"]) if len(z) else pd.DataFrame()
    oneri = {}
    for s_, satir in tablo.iterrows():
        en = satir.idxmax()
        oneri[str(int(s_))] = {"ad": en, "destek": f"{int(satir.max())}/{int(satir.sum())}"}
    dogru = sum(int(tablo.loc[int(k), v["ad"]]) for k, v in oneri.items()) if len(tablo) else 0
    sonuc["zemin"] = {"kullanilan": int(len(z)), "uyum_yuzde": round(100 * dogru / max(1, len(z)), 1),
                      "siniflar": {str(k): v for k, v in adlar.items()}, "oneri": oneri,
                      "tablo": {str(int(k)): {c_: int(v) for c_, v in r_.items()} for k, r_ in tablo.iterrows()}}

ham.drop(columns=["ux", "uy"]).round(4).to_csv(os.path.join(OUT, "dogrulama_sonuclari.csv"), index=False, encoding="utf-8-sig")
with open("cozumleme/web/dogrulama.json", "w", encoding="utf-8") as f:
    json.dump(sonuc, f, ensure_ascii=False)
print(json.dumps(sonuc, ensure_ascii=False))
print("@@ilerleme 1.0")
