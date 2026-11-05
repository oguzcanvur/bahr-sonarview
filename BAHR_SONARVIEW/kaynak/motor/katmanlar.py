"""Arayuz icin harita katmanlari ve ozet verileri (cozumleme/web/).

Kullanim:  python katmanlar.py temel|zemin|uydu|taramalar
"""
import json
import math
import os
import sys

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.tri as mtri
from matplotlib import colormaps
from PIL import Image

WEB = "cozumleme/web"
os.makedirs(WEB, exist_ok=True)
META = "cozumleme/meta/B001_ds_hifreq_meta.csv"
COZ = 0.5          # raster cozunurlugu (m)


def yaz(ad, obj):
    with open(os.path.join(WEB, ad), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":"), allow_nan=False,
                  default=lambda o: None)


def temiz(x, n=6):
    """NaN/inf -> None, float yuvarla (JSON icin)."""
    a = np.asarray(x, float)
    return [None if not np.isfinite(v) else round(float(v), n) for v in a]


class Yerel:
    """lat/lon <-> yerel metre (kucuk alanlar icin esdikdortgen yaklasimi)."""

    def __init__(self, lat0, lon0):
        self.lat0, self.lon0 = lat0, lon0
        self.kx = 111320 * math.cos(math.radians(lat0))
        self.ky = 110574.0

    def xy(self, lat, lon):
        return (np.asarray(lon) - self.lon0) * self.kx, (np.asarray(lat) - self.lat0) * self.ky

    def ll(self, x, y):
        return self.lat0 + np.asarray(y) / self.ky, self.lon0 + np.asarray(x) / self.kx


def raster(lat, lon, val, ad, cmap, vmin, vmax, max_kenar=7.0, kategorik=None, alpha=0.82):
    """Nokta verisinden (lat, lon, deger) seffaf PNG katmani + sinirlari."""
    Y = Yerel(float(np.mean(lat)), float(np.mean(lon)))
    x, y = Y.xy(lat, lon)
    t = mtri.Triangulation(x, y)
    p = np.c_[x, y][t.triangles]
    e = np.max([np.hypot(*(p[:, i] - p[:, (i + 1) % 3]).T) for i in range(3)], axis=0)
    t.set_mask(e > max_kenar)
    xs = np.arange(x.min(), x.max() + COZ, COZ)
    ys = np.arange(y.min(), y.max() + COZ, COZ)
    GX, GY = np.meshgrid(xs, ys[::-1])           # ust satir = kuzey
    Z = mtri.LinearTriInterpolator(t, val)(GX, GY).filled(np.nan)
    rgba = np.zeros(Z.shape + (4,), np.uint8)
    m = np.isfinite(Z)
    if kategorik is not None:
        idx = np.clip(np.rint(Z[m]).astype(int), 0, len(kategorik) - 1)
        renk = np.array([[int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16)] for c in kategorik])
        rgba[m, :3] = renk[idx]
    else:
        cm = colormaps[cmap]
        rgba[m] = (np.array(cm(np.clip((Z[m] - vmin) / max(vmax - vmin, 1e-9), 0, 1))) * 255).astype(np.uint8)
    rgba[m, 3] = int(alpha * 255)
    Image.fromarray(rgba, "RGBA").save(os.path.join(WEB, ad), optimize=True)
    la0, lo0 = Y.ll(xs[0] - COZ / 2, ys[0] - COZ / 2)
    la1, lo1 = Y.ll(xs[-1] + COZ / 2, ys[-1] + COZ / 2)
    return {"png": ad, "sinir": [[float(la0), float(lo0)], [float(la1), float(lo1)]]}


def konturlar(lat, lon, val, seviyeler, max_kenar=7.0):
    Y = Yerel(float(np.mean(lat)), float(np.mean(lon)))
    x, y = Y.xy(lat, lon)
    t = mtri.Triangulation(x, y)
    p = np.c_[x, y][t.triangles]
    e = np.max([np.hypot(*(p[:, i] - p[:, (i + 1) % 3]).T) for i in range(3)], axis=0)
    t.set_mask(e > max_kenar)
    fig, ax = plt.subplots()
    cs = ax.tricontour(t, val, levels=seviyeler)
    ozellik = []
    for sev, segs in zip(cs.levels, cs.allsegs):
        for s in segs:
            if len(s) < 3:
                continue
            la, lo = Y.ll(s[:, 0], s[:, 1])
            ozellik.append({"type": "Feature", "properties": {"derinlik": round(float(sev), 2)},
                            "geometry": {"type": "LineString",
                                         "coordinates": [[round(float(b), 7), round(float(a), 7)] for a, b in zip(la, lo)]}})
    plt.close(fig)
    return {"type": "FeatureCollection", "features": ozellik}


def noktalar(df, ozellikler):
    return {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {k: (None if (isinstance(r[k], float) and not np.isfinite(r[k])) else
                                               (r[k].item() if hasattr(r[k], "item") else r[k])) for k in ozellikler},
         "geometry": {"type": "Point", "coordinates": [round(float(r["lon"]), 7), round(float(r["lat"]), 7)]}}
        for _, r in df.iterrows()]}


def kontur_seviyeleri(v):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from uydu_altlik import kontur_seviyeleri as ks
    return ks(v)


# ====================================================================== TEMEL
def temel():
    full = pd.read_csv(META)
    full["satir"] = np.arange(len(full))
    has = full["inst_dep_m"].notna()
    seg = (has.astype(int).diff() != 0).cumsum()
    d = full[has & (has.groupby(seg).transform("sum") >= 1000)].copy()
    d["dsm"] = d["inst_dep_m"].rolling(51, center=True, min_periods=10).median()
    hiz = full["speed_ms"].where(full["speed_ms"] < 5)
    gps = (full["lat"].abs() > 0.01)
    dat = pd.read_csv("cozumleme/meta/DAT_meta.csv").iloc[0].to_dict() if os.path.exists("cozumleme/meta/DAT_meta.csv") else {}
    bat = pd.read_csv("cozumleme/grafikler/batimetri_grid_1m.csv")
    ilk, son = full.iloc[0], full.iloc[-1]
    sure = float(full["time_s"].iloc[-1] - full["time_s"].iloc[0])
    alan = None
    try:
        Y = Yerel(bat["lat"].mean(), bat["lon"].mean())
        x, y = Y.xy(bat["lat"], bat["lon"])
        t = mtri.Triangulation(x, y)
        p = np.c_[x, y][t.triangles]
        e = np.max([np.hypot(*(p[:, i] - p[:, (i + 1) % 3]).T) for i in range(3)], axis=0)
        a_ = 0.5 * np.abs((p[:, 1, 0] - p[:, 0, 0]) * (p[:, 2, 1] - p[:, 0, 1]) - (p[:, 2, 0] - p[:, 0, 0]) * (p[:, 1, 1] - p[:, 0, 1]))
        alan = float(a_[e <= 7.0].sum())
    except Exception:
        pass
    ozet = {
        "tarih": str(ilk["date"]), "baslangic": str(ilk["time"])[:8], "bitis": str(son["time"])[:8],
        "sure_dk": round(sure / 60, 1), "ping": int(len(full)), "ping_hz": round(len(full) / max(sure, 1), 1),
        "yol_m": round(float(full["trk_dist"].max()), 0), "hiz_ort_kmsa": round(float(hiz[hiz > 0.1].median() * 3.6), 2),
        "derinlik_min": round(float(d["dsm"].quantile(0.005)), 2), "derinlik_max": round(float(d["dsm"].quantile(0.995)), 2),
        "derinlik_medyan": round(float(d["dsm"].median()), 2),
        "sicaklik_min": round(float(full["tempC"].min()), 1), "sicaklik_max": round(float(full["tempC"].max()), 1),
        "sicaklik_medyan": round(float(full["tempC"].median()), 1),
        "haritalanan_alan_m2": None if alan is None else round(alan),
        "elenen_ping": int((~(has & (has.groupby(seg).transform("sum") >= 1000))).sum()),
        "cihaz_urun_no": int(dat.get("unit_product_number", 0) or 0),
        "kanal": "DownVü (aşağı bakan, yüksek frekans)",
        "dosya_mb": round(os.path.getsize("ham.RSD") / 1e6, 1),
        "merkez": [round(float(full.loc[gps, "lat"].median()), 7), round(float(full.loc[gps, "lon"].median()), 7)],
        "sinir": [[float(full.loc[gps, "lat"].min()), float(full.loc[gps, "lon"].min())],
                  [float(full.loc[gps, "lat"].max()), float(full.loc[gps, "lon"].max())]],
        "kesit_derinlik_max": float(np.ceil(max(2.0, d["dsm"].quantile(0.995) * 1.25))),
        "toplam_satir": int(len(full)),
    }
    yaz("ozet.json", ozet)

    # rota (her ~0,4 sn bir nokta)
    st = max(1, int(round(ozet["ping_hz"] * 0.4)))
    r = full[gps].iloc[::st]
    dep = d["dsm"].reindex(full.index)
    yaz("rota.json", {"lat": temiz(r["lat"], 7), "lon": temiz(r["lon"], 7), "dep": temiz(dep[r.index], 2),
                      "t": temiz(r["time_s"], 1), "satir": [int(v) for v in r["satir"]]})
    # zaman serisi (~1 Hz)
    st = max(1, int(round(ozet["ping_hz"])))
    z = full.iloc[::st]
    yaz("zaman.json", {"t": temiz(z["time_s"] / 60, 3), "dep": temiz(dep[z.index], 2),
                       "hiz": temiz(hiz.rolling(51, center=True, min_periods=5).median()[z.index] * 3.6, 2),
                       "sic": temiz(z["tempC"], 2), "satir": [int(v) for v in z["satir"]]})
    # batimetri katmani + konturlar
    vmax = float(bat["derinlik_m"].quantile(0.99))
    vmin = float(bat["derinlik_m"].quantile(0.01))
    k = raster(bat["lat"].to_numpy(), bat["lon"].to_numpy(), bat["derinlik_m"].to_numpy(), "batimetri.png",
               "viridis_r", vmin, vmax)
    k.update({"min": round(vmin, 2), "max": round(vmax, 2), "cmap": "viridis_r"})
    sev = kontur_seviyeleri(bat["derinlik_m"])
    yaz("katman_batimetri.json", k)
    yaz("kontur.geojson", konturlar(bat["lat"].to_numpy(), bat["lon"].to_numpy(), bat["derinlik_m"].to_numpy(), sev))
    # renk skalasi ornegi (arayuz efsanesi icin)
    cm = colormaps["viridis_r"]
    yaz("renk_viridis_r.json", ["#%02x%02x%02x" % tuple(int(255 * c) for c in cm(i / 10)[:3]) for i in range(11)])


# ====================================================================== ZEMIN
def zemin():
    g = pd.read_csv("cozumleme/zemin/zemin_grid_1m.csv")
    g = g[g["sinif"] >= 0]
    renk = ["#8c510a", "#dfc27d", "#35978f"]
    k = raster(g["lat"].to_numpy(), g["lon"].to_numpy(), g["sinif"].to_numpy(float), "zemin.png", None, 0, 2,
               kategorik=renk, alpha=0.7)
    oz = pd.read_csv("cozumleme/zemin/zemin_sinif_ozeti.csv")
    k["siniflar"] = [{"sinif": int(r["sinif"]), "ad": str(r["yorum"]), "renk": renk[int(r["sinif"])],
                      "alan_yuzde": float(r["alan_yuzde"]), "derinlik": float(r["derinlik"])} for _, r in oz.iterrows()]
    yaz("katman_zemin.json", k)
    for c, ad, cmap in [("peak", "sertlik", "YlOrBr"), ("contrast", "penetrasyon", "PuBu")]:
        v = g[c].to_numpy(float)
        lo, hi = np.nanpercentile(v, [3, 97])
        kk = raster(g["lat"].to_numpy(), g["lon"].to_numpy(), v, f"{ad}.png", cmap, lo, hi, alpha=0.78)
        kk.update({"min": None, "max": None})
        yaz(f"katman_{ad}.json", kk)
    n = pd.read_csv("cozumleme/zemin/numune_noktalari.csv")
    n = n.rename(columns={"enlem": "lat", "boylam": "lon"})
    yaz("numune.geojson", noktalar(n, ["nokta", "beklenen_zemin", "derinlik_m", "kapsama_yuzde"]))


# ====================================================================== UYDU / HACIM / ROTA
def uydu():
    oz = pd.read_csv("cozumleme/morfoloji/morfoloji_ozet.csv", index_col=0)["deger"]
    yaz("hacim.json", {k: (None if pd.isna(v) else float(v)) for k, v in oz.items()})
    gg = pd.read_csv("cozumleme/morfoloji/tum_golet_grid.csv")
    vmax = float(gg["derinlik"].quantile(0.99))
    k = raster(gg["lat"].to_numpy(), gg["lon"].to_numpy(), gg["derinlik"].to_numpy(), "tum_golet.png",
               "viridis_r", 0.0, vmax, max_kenar=3.0, alpha=0.75)
    k.update({"min": 0.0, "max": round(vmax, 2)})
    yaz("katman_tum_golet.json", k)
    rp = pd.read_csv("cozumleme/morfoloji/yeni_rota_noktalari.csv")
    yaz("yeni_rota.json", {"lat": temiz(rp["lat"], 7), "lon": temiz(rp["lon"], 7), "hat": [int(h) for h in rp["hat"]]})
    if os.path.exists("cozumleme/morfoloji/kiyi_noktalari.csv"):
        kn = pd.read_csv("cozumleme/morfoloji/kiyi_noktalari.csv")
        yaz("kiyi.json", {"lat": temiz(kn["lat"], 7), "lon": temiz(kn["lon"], 7)})


# ====================================================================== TARAMALAR
def taramalar():
    out = {}
    if os.path.exists("cozumleme/balik/su_kolonu_hedefleri.csv"):
        h = pd.read_csv("cozumleme/balik/su_kolonu_hedefleri.csv")
        h = h[h["tur"].isin(["balik", "kabarcik"])]
        h["dk"] = (h["time_s"] / 60).round(1)
        h["derinlik"] = h["derinlik"].round(2)
        yaz("balik.geojson", noktalar(h, ["tur", "derinlik", "dk", "ping"]))
        out["balik"] = int((h["tur"] == "balik").sum())
        out["kabarcik"] = int((h["tur"] == "kabarcik").sum())
    if os.path.exists("cozumleme/sertnokta/sert_nokta_adaylari.csv"):
        s = pd.read_csv("cozumleme/sertnokta/sert_nokta_adaylari.csv")
        yaz("sertnokta.geojson", noktalar(s, ["no", "tur", "derinlik", "guven"]) if len(s) else
            {"type": "FeatureCollection", "features": []})
        out["sert_nokta"] = int(len(s))
    if os.path.exists("cozumleme/bitki/bitki_grid_1m.csv"):
        b = pd.read_csv("cozumleme/bitki/bitki_grid_1m.csv")
        out["bitki_kaplama_ort_yuzde"] = round(float(b["kaplama"].mean() * 100), 2)
    yaz("taramalar.json", out)


if __name__ == "__main__":
    {"temel": temel, "zemin": zemin, "uydu": uydu, "taramalar": taramalar}[sys.argv[1]]()
    print("@@ilerleme 1.0")
