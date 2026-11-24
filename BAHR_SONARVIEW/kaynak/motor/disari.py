"""Muhendislik ciktilari: CBS ve CAD formatlari, secilen koordinat sisteminde.

  GeoTIFF : derinlik ve kot izgarasi (olculen alan; uydu analizi varsa tum su alani)
  Shapefile (.shp/.dbf/.shx/.prj/.cpg): konturlar, rota, olcum noktalari, zemin, numune, notlar, ...
  GeoJSON, KML (Google Earth) : WGS84 (bicim geregi)
  DXF (R12) : es derinlik cizgileri 3B (Z = kot), rota, noktalar, etiketler
  XYZ / CSV : izgara ve olcum noktalari
Tumu cozumleme/disari/ altina ve tek bir zip dosyasina yazilir.
"""
import json
import math
import os
import re
import shutil
import zipfile
from datetime import datetime

import numpy as np
import pandas as pd
from PIL import Image, TiffImagePlugin
from pyproj import CRS, Transformer

from ortak import KOORDINAT_ADLARI, koordinat_sistemi, parametreler

P = parametreler()
OUT = "cozumleme/disari"
shutil.rmtree(OUT, ignore_errors=True)
os.makedirs(OUT)
SU_KOTU = float(P.get("su_kotu") or 0.0)
NODATA = -9999.0


def oku_json(yol):
    if not os.path.exists(yol):
        return None
    with open(yol, encoding="utf-8") as f:
        return json.load(f)


oz = oku_json("cozumleme/web/ozet.json") or {}
proje = oku_json("proje.json") or {}
lat0, lon0 = (oz.get("merkez") or [39.0, 35.0])
KOD = P.get("koordinat") or "utm"
CRS_HEDEF, CRS_AD, EPSG = koordinat_sistemi(KOD, lon0)
COGRAFI = CRS_HEDEF.is_geographic
ll2h = Transformer.from_crs(4326, CRS_HEDEF, always_xy=True)
ESRI_WKT = CRS_HEDEF.to_wkt("WKT1_ESRI")
yazilan = []


def dosya(ad):
    yol = os.path.join(OUT, ad)
    yazilan.append(yol)
    return yol


def donustur(lon, lat):
    x, y = ll2h.transform(np.asarray(lon, float), np.asarray(lat, float))
    return np.asarray(x), np.asarray(y)


# ====================================================================== GeoTIFF
def geotiff_yaz(yol, A, x0, y1, sx, sy, epsg, cografi):
    A = np.where(np.isfinite(A), A, NODATA).astype(np.float32)
    ifd = TiffImagePlugin.ImageFileDirectory_v2()
    ifd[33550] = (float(sx), float(sy), 0.0)                      # ModelPixelScale
    ifd.tagtype[33550] = 12
    ifd[33922] = (0.0, 0.0, 0.0, float(x0), float(y1), 0.0)       # ModelTiepoint (sol ust kose)
    ifd.tagtype[33922] = 12
    if cografi:
        keys = [1, 1, 0, 3, 1024, 0, 1, 2, 1025, 0, 1, 1, 2048, 0, 1, int(epsg)]
    else:
        keys = [1, 1, 0, 3, 1024, 0, 1, 1, 1025, 0, 1, 1, 3072, 0, 1, int(epsg)]
    ifd[34735] = tuple(keys)                                      # GeoKeyDirectory
    ifd.tagtype[34735] = 3
    ifd[42113] = str(int(NODATA))                                 # GDAL_NODATA
    ifd.tagtype[42113] = 2
    Image.fromarray(A, mode="F").save(yol, tiffinfo=ifd, compression="tiff_deflate")


def yeniden_ornekle(Z, x0, y1, h, kaynak_epsg):
    """UTM izgarasini hedef koordinat sistemine en yakin komsu ile tasir."""
    if not COGRAFI and EPSG == kaynak_epsg:
        return Z, x0, y1, h, h
    ny, nx = Z.shape
    kay = CRS.from_epsg(kaynak_epsg)
    k2h = Transformer.from_crs(kay, CRS_HEDEF, always_xy=True)
    h2k = Transformer.from_crs(CRS_HEDEF, kay, always_xy=True)
    kx = np.array([x0, x0 + nx * h, x0, x0 + nx * h])
    ky = np.array([y1, y1, y1 - ny * h, y1 - ny * h])
    hx, hy = k2h.transform(kx, ky)
    if COGRAFI:
        sx = h / (111320 * math.cos(math.radians(lat0)))
        sy = h / 110574.0
    else:
        sx = sy = h
    X0, X1, Y0, Y1 = hx.min(), hx.max(), hy.min(), hy.max()
    W, H = int(np.ceil((X1 - X0) / sx)), int(np.ceil((Y1 - Y0) / sy))
    GX, GY = np.meshgrid(X0 + (np.arange(W) + 0.5) * sx, Y1 - (np.arange(H) + 0.5) * sy)
    ux, uy = h2k.transform(GX, GY)
    c = np.floor((ux - x0) / h).astype(int)
    r = np.floor((y1 - uy) / h).astype(int)
    ok = (c >= 0) & (c < nx) & (r >= 0) & (r < ny)
    out = np.full((H, W), np.nan, np.float32)
    out[ok] = Z[r[ok], c[ok]]
    return out, X0, Y1, sx, sy


def nokta_rasteri(lon, lat, val, h=1.0):
    """Duzensiz noktalari hedef koordinat sisteminde izgaraya ortalar."""
    x, y = donustur(lon, lat)
    if COGRAFI:
        sx, sy = h / (111320 * math.cos(math.radians(lat0))), h / 110574.0
    else:
        sx = sy = h
    X0, Y1 = x.min() - sx, y.max() + sy
    c = ((x - X0) / sx).astype(int)
    r = ((Y1 - y) / sy).astype(int)
    W, H = c.max() + 2, r.max() + 2
    top = np.zeros((H, W))
    say = np.zeros((H, W))
    np.add.at(top, (r, c), val)
    np.add.at(say, (r, c), 1)
    return np.where(say > 0, top / np.maximum(say, 1), np.nan), X0, Y1, sx, sy


izg = None
if os.path.exists("cozumleme/grafikler/derinlik_izgara.npz"):
    izg = np.load("cozumleme/grafikler/derinlik_izgara.npz")
    Z = izg["Z"].astype(float)
    A, X0, Y1, sx, sy = yeniden_ornekle(Z, float(izg["x0"]), float(izg["y1"]), float(izg["hucre"]), int(izg["epsg"]))
    geotiff_yaz(dosya("derinlik_olculen.tif"), A, X0, Y1, sx, sy, EPSG, COGRAFI)
    geotiff_yaz(dosya("kot_olculen.tif"), SU_KOTU - A, X0, Y1, sx, sy, EPSG, COGRAFI)
TUM = "cozumleme/morfoloji/tum_golet_grid.csv"
if os.path.exists(TUM):
    tg = pd.read_csv(TUM)
    A, X0, Y1, sx, sy = nokta_rasteri(tg["lon"], tg["lat"], tg["derinlik"].to_numpy(float))
    geotiff_yaz(dosya("derinlik_tum_su_alani.tif"), A, X0, Y1, sx, sy, EPSG, COGRAFI)
    geotiff_yaz(dosya("kot_tum_su_alani.tif"), SU_KOTU - A, X0, Y1, sx, sy, EPSG, COGRAFI)
print("@@ilerleme 0.3", flush=True)

# ====================================================================== vektor katmanlar
# her katman: ad -> {"tur": "cizgi"|"nokta", "ozellikler": [(geometri lon/lat listesi, {alanlar})]}
KATMAN = {}

kon = oku_json("cozumleme/web/kontur.geojson")
if kon:
    KATMAN["konturlar"] = {"tur": "cizgi", "ozellikler": [
        (f["geometry"]["coordinates"], {"DERINLIK": f["properties"]["derinlik"], "KOT": round(SU_KOTU - f["properties"]["derinlik"], 3)})
        for f in kon["features"]]}
rota = oku_json("cozumleme/web/rota.json")
if rota:
    pts = [[lo, la] for la, lo in zip(rota["lat"], rota["lon"]) if la is not None and lo is not None]
    KATMAN["rota"] = {"tur": "cizgi", "ozellikler": [(pts, {"AD": "Tarama rotasi"})]}
if os.path.exists("cozumleme/grafikler/batimetri_grid_1m.csv"):
    b = pd.read_csv("cozumleme/grafikler/batimetri_grid_1m.csv").dropna(subset=["derinlik_m"])
    KATMAN["olcum_noktalari"] = {"tur": "nokta", "ozellikler": [
        ([r.lon, r.lat], {"DERINLIK": round(r.derinlik_m, 3), "KOT": round(SU_KOTU - r.derinlik_m, 3), "PING": int(r.ping_sayisi)})
        for r in b.itertuples()]}
if os.path.exists("cozumleme/zemin/zemin_grid_1m.csv"):
    z = pd.read_csv("cozumleme/zemin/zemin_grid_1m.csv")
    z = z[z["sinif"] >= 0]
    ad = {}
    if os.path.exists("cozumleme/zemin/zemin_sinif_ozeti.csv"):
        so = pd.read_csv("cozumleme/zemin/zemin_sinif_ozeti.csv")
        ad = {int(r["sinif"]): str(r["yorum"]) for _, r in so.iterrows()}
    KATMAN["zemin_siniflari"] = {"tur": "nokta", "ozellikler": [
        ([r.lon, r.lat], {"SINIF": int(r.sinif), "YORUM": ad.get(int(r.sinif), "")[:80]}) for r in z.itertuples()]}
if os.path.exists("cozumleme/zemin/numune_noktalari.csv"):
    n = pd.read_csv("cozumleme/zemin/numune_noktalari.csv")
    KATMAN["numune_noktalari"] = {"tur": "nokta", "ozellikler": [
        ([r.boylam, r.enlem], {"NOKTA": str(r.nokta), "ZEMIN": str(r.beklenen_zemin)[:80], "DERINLIK": round(float(r.derinlik_m), 2)})
        for r in n.itertuples()]}
if os.path.exists("cozumleme/morfoloji/yeni_rota_noktalari.csv"):
    yr = pd.read_csv("cozumleme/morfoloji/yeni_rota_noktalari.csv")
    KATMAN["onerilen_rota"] = {"tur": "cizgi", "ozellikler": [([[r.lon, r.lat] for r in yr.itertuples()], {"AD": "Onerilen tarama rotasi"})]}
if os.path.exists("cozumleme/balik/su_kolonu_hedefleri.csv"):
    h = pd.read_csv("cozumleme/balik/su_kolonu_hedefleri.csv")
    h = h[h["tur"].isin(["balik", "kabarcik"])]
    if len(h):
        KATMAN["balik_kabarcik"] = {"tur": "nokta", "ozellikler": [
            ([r.lon, r.lat], {"TUR": str(r.tur), "DERINLIK": round(float(r.derinlik), 2)}) for r in h.itertuples()]}
if os.path.exists("cozumleme/sertnokta/sert_nokta_adaylari.csv"):
    s = pd.read_csv("cozumleme/sertnokta/sert_nokta_adaylari.csv")
    if len(s):
        KATMAN["sert_noktalar"] = {"tur": "nokta", "ozellikler": [
            ([r.lon, r.lat], {"NO": str(r.no), "TUR": str(r.tur)[:60], "DERINLIK": round(float(r.derinlik), 2)}) for r in s.itertuples()]}
notlar = oku_json("notlar.json") or []
if notlar:
    KATMAN["notlar"] = {"tur": "nokta", "ozellikler": [
        ([n["lon"], n["lat"]], {"BASLIK": str(n.get("baslik", ""))[:80], "METIN": str(n.get("metin", ""))[:250]}) for n in notlar]}


# ---------------------------------------------------------------- Shapefile
def shp_yaz(ad, k):
    import shapefile
    tur = shapefile.POLYLINE if k["tur"] == "cizgi" else shapefile.POINT
    taban = os.path.join(OUT, "shp", ad)
    os.makedirs(os.path.dirname(taban), exist_ok=True)
    alanlar = list(k["ozellikler"][0][1].keys())
    with shapefile.Writer(taban, shapeType=tur, encoding="utf-8") as w:
        for a in alanlar:
            ornek = k["ozellikler"][0][1][a]
            if isinstance(ornek, int):
                w.field(a, "N", 10, 0)
            elif isinstance(ornek, float):
                w.field(a, "N", 14, 3)
            else:
                w.field(a, "C", 254)
        for geo, al in k["ozellikler"]:
            g = np.asarray(geo, float).reshape(-1, 2)
            x, y = donustur(g[:, 0], g[:, 1])
            if k["tur"] == "cizgi":
                if len(x) < 2:
                    continue
                w.line([list(zip(x.tolist(), y.tolist()))])
            else:
                w.point(float(x[0]), float(y[0]))
            w.record(*[al[a] for a in alanlar])
    with open(taban + ".prj", "w") as f:
        f.write(ESRI_WKT)
    with open(taban + ".cpg", "w") as f:
        f.write("UTF-8")
    for uz in (".shp", ".shx", ".dbf", ".prj", ".cpg"):
        yazilan.append(taban + uz)


for ad, k in KATMAN.items():
    if k["ozellikler"]:
        shp_yaz(ad, k)
print("@@ilerleme 0.55", flush=True)

# ---------------------------------------------------------------- GeoJSON (WGS84)
for ad, k in KATMAN.items():
    fs = [{"type": "Feature", "properties": al,
           "geometry": {"type": "LineString" if k["tur"] == "cizgi" else "Point",
                        "coordinates": [[round(a, 7), round(b, 7)] for a, b in geo] if k["tur"] == "cizgi" else [round(geo[0], 7), round(geo[1], 7)]}}
          for geo, al in k["ozellikler"]]
    os.makedirs(os.path.join(OUT, "geojson"), exist_ok=True)
    with open(dosya(f"geojson/{ad}.geojson"), "w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection", "name": ad, "features": fs}, f, ensure_ascii=False)


# ---------------------------------------------------------------- KML (Google Earth)
def x(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


RENK = {"konturlar": "ffffffff", "rota": "ff00d7ff", "onerilen_rota": "ff15ccfa"}
kml = ['<?xml version="1.0" encoding="UTF-8"?>', '<kml xmlns="http://www.opengis.net/kml/2.2"><Document>',
       f'<name>{x(proje.get("ad", "BAHR SONARVIEW"))}</name>']
for ad, renk in RENK.items():
    kml.append(f'<Style id="{ad}"><LineStyle><color>{renk}</color><width>{2 if ad != "konturlar" else 1.2}</width></LineStyle></Style>')
kml.append('<Style id="nokta"><IconStyle><scale>0.7</scale></IconStyle><LabelStyle><scale>0.7</scale></LabelStyle></Style>')
for ad, k in KATMAN.items():
    if ad in ("olcum_noktalari", "zemin_siniflari"):           # Google Earth icin fazla yogun
        continue
    kml.append(f'<Folder><name>{x(ad.replace("_", " ").capitalize())}</name>')
    for geo, al in k["ozellikler"]:
        if k["tur"] == "cizgi":
            ad_ = f'{al["DERINLIK"]} m' if "DERINLIK" in al else al.get("AD", ad)
            kml.append(f'<Placemark><name>{x(ad_)}</name><styleUrl>#{ad if ad in RENK else "rota"}</styleUrl><LineString><tessellate>1</tessellate><coordinates>'
                       + " ".join(f"{a:.7f},{b:.7f},0" for a, b in geo) + "</coordinates></LineString></Placemark>")
        else:
            ad_ = al.get("NOKTA") or al.get("BASLIK") or al.get("NO") or al.get("TUR") or ""
            acik = "<br>".join(f"{x(a)}: {x(v)}" for a, v in al.items())
            kml.append(f'<Placemark><name>{x(ad_)}</name><description><![CDATA[{acik}]]></description><styleUrl>#nokta</styleUrl>'
                       f'<Point><coordinates>{geo[0]:.7f},{geo[1]:.7f},0</coordinates></Point></Placemark>')
    kml.append("</Folder>")
kml.append("</Document></kml>")
with open(dosya("google_earth.kml"), "w", encoding="utf-8") as f:
    f.write("\n".join(kml))


# ---------------------------------------------------------------- DXF (R12, AutoCAD / NetCAD)
class Dxf:
    def __init__(self):
        self.e = []
        self.katmanlar = {}

    def katman(self, ad, renk):
        self.katmanlar[ad] = renk

    def cizgi3b(self, ad, pts):
        self.e += ["0", "POLYLINE", "8", ad, "66", "1", "10", "0", "20", "0", "30", "0", "70", "8"]
        for px, py, pz in pts:
            self.e += ["0", "VERTEX", "8", ad, "10", f"{px:.3f}", "20", f"{py:.3f}", "30", f"{pz:.3f}", "70", "32"]
        self.e += ["0", "SEQEND", "8", ad]

    def nokta(self, ad, px, py, pz):
        self.e += ["0", "POINT", "8", ad, "10", f"{px:.3f}", "20", f"{py:.3f}", "30", f"{pz:.3f}"]

    def yazi(self, ad, px, py, pz, metin, boy):
        metin = re.sub(r"[^\x20-\x7e]", lambda m: {"ı": "i", "İ": "I", "ş": "s", "Ş": "S", "ğ": "g", "Ğ": "G", "ü": "u", "Ü": "U",
                                                     "ö": "o", "Ö": "O", "ç": "c", "Ç": "C", "²": "2", "³": "3"}.get(m.group(), "?"), metin)
        self.e += ["0", "TEXT", "8", ad, "10", f"{px:.3f}", "20", f"{py:.3f}", "30", f"{pz:.3f}", "40", f"{boy:.2f}", "1", metin]

    def yaz(self, yol):
        s = ["0", "SECTION", "2", "HEADER", "9", "$ACADVER", "1", "AC1009", "9", "$INSUNITS", "70", "6", "0", "ENDSEC",
             "0", "SECTION", "2", "TABLES", "0", "TABLE", "2", "LAYER", "70", str(len(self.katmanlar))]
        for ad, renk in self.katmanlar.items():
            s += ["0", "LAYER", "2", ad, "70", "0", "62", str(renk), "6", "CONTINUOUS"]
        s += ["0", "ENDTAB", "0", "ENDSEC", "0", "SECTION", "2", "ENTITIES"] + self.e + ["0", "ENDSEC", "0", "EOF"]
        with open(yol, "w", encoding="ascii", newline="\r\n") as f:
            f.write("\n".join(s) + "\n")


if not COGRAFI:
    dx = Dxf()
    for ad, renk in [("KONTUR", 5), ("KONTUR_ETIKET", 5), ("ROTA", 1), ("ONERILEN_ROTA", 2), ("OLCUM_NOKTA", 8),
                     ("NUMUNE", 6), ("NOTLAR", 3), ("SERT_NOKTA", 1)]:
        dx.katman(ad, renk)
    for geo, al in KATMAN.get("konturlar", {}).get("ozellikler", []):
        g = np.asarray(geo, float)
        xx, yy = donustur(g[:, 0], g[:, 1])
        dx.cizgi3b("KONTUR", [(a, b, al["KOT"]) for a, b in zip(xx, yy)])
        m = len(xx) // 2
        dx.yazi("KONTUR_ETIKET", xx[m], yy[m], al["KOT"], f'{al["DERINLIK"]:.2f}', 0.6)
    for katman, dad in [("rota", "ROTA"), ("onerilen_rota", "ONERILEN_ROTA")]:
        for geo, al in KATMAN.get(katman, {}).get("ozellikler", []):
            g = np.asarray(geo, float)
            xx, yy = donustur(g[:, 0], g[:, 1])
            dx.cizgi3b(dad, [(a, b, SU_KOTU) for a, b in zip(xx, yy)])
    for katman, dad, etiket in [("olcum_noktalari", "OLCUM_NOKTA", None), ("numune_noktalari", "NUMUNE", "NOKTA"),
                                ("notlar", "NOTLAR", "BASLIK"), ("sert_noktalar", "SERT_NOKTA", "NO")]:
        for geo, al in KATMAN.get(katman, {}).get("ozellikler", []):
            xx, yy = donustur([geo[0]], [geo[1]])
            zz = al.get("KOT", SU_KOTU - al.get("DERINLIK", 0) if "DERINLIK" in al else SU_KOTU)
            dx.nokta(dad, xx[0], yy[0], zz)
            if etiket:
                dx.yazi(dad, xx[0] + 0.8, yy[0] + 0.8, zz, str(al.get(etiket, "")), 0.9)
    dx.yaz(dosya("cizim_R12.dxf"))
print("@@ilerleme 0.8", flush=True)

# ---------------------------------------------------------------- XYZ / CSV
if izg is not None:
    Z = izg["Z"].astype(float)
    r, c = np.nonzero(np.isfinite(Z))
    h = float(izg["hucre"])
    ux = float(izg["x0"]) + (c + 0.5) * h
    uy = float(izg["y1"]) - (r + 0.5) * h
    lon, lat = Transformer.from_crs(CRS.from_epsg(int(izg["epsg"])), 4326, always_xy=True).transform(ux, uy)
    hx, hy = donustur(lon, lat)
    dep = Z[r, c]
    nd = 8 if COGRAFI else 3
    with open(dosya("izgara_kot.xyz"), "w") as f:
        f.writelines(f"{a:.{nd}f} {b:.{nd}f} {SU_KOTU - d:.3f}\n" for a, b, d in zip(hx, hy, dep))
    pd.DataFrame({"x": np.round(hx, nd), "y": np.round(hy, nd), "derinlik_m": np.round(dep, 3), "kot_m": np.round(SU_KOTU - dep, 3),
                  "olculdu": izg["N"][r, c] > 0}).to_csv(dosya("izgara.csv"), index=False)
if "olcum_noktalari" in KATMAN:
    with open(dosya("olcum_noktalari_kot.xyz"), "w") as f:
        for geo, al in KATMAN["olcum_noktalari"]["ozellikler"]:
            xx, yy = donustur([geo[0]], [geo[1]])
            f.write(f"{xx[0]:.{8 if COGRAFI else 3}f} {yy[0]:.{8 if COGRAFI else 3}f} {al['KOT']:.3f}\n")

# ---------------------------------------------------------------- aciklama + zip
bilgi = f"""BAHR SONARVIEW - muhendislik ciktilari
Proje           : {proje.get("ad", "")}
Olusturma       : {datetime.now():%Y-%m-%d %H:%M}
Koordinat sist. : {CRS_AD} (EPSG:{EPSG}) - {KOORDINAT_ADLARI.get(KOD, KOD)}
Dusey referans  : Z = kot (m) = su yuzeyi kotu - derinlik ; su yuzeyi kotu = {SU_KOTU:.3f} m (proje ayari)
Derinlik        : su yuzeyinden asagi pozitif (m); batma payi = {float(P.get("batma_payi") or 0):.2f} m eklendi
Ses hizi        : {P.get("ses_hizi_modu")} (cihazin varsaydigi {P.get("cihaz_ses_hizi")} m/s)

Dosyalar
  derinlik_*.tif / kot_*.tif : GeoTIFF izgara (1 m), bos hucre = {int(NODATA)}
  shp/                       : ESRI Shapefile katmanlari (+ .prj, UTF-8)
  geojson/                   : GeoJSON (WGS84, bicim geregi)
  google_earth.kml           : Google Earth (WGS84)
  cizim_R12.dxf              : AutoCAD / NetCAD (R12; konturlar 3B, Z = kot){"  -- cografi koordinatta uretilmez" if COGRAFI else ""}
  izgara_kot.xyz, izgara.csv : izgara noktalari
  olcum_noktalari_kot.xyz    : olculen 1 m hucre medyanlari

Not: ED50 donusumleri EPSG'deki 7 parametreli donusumle yapilir (birkac metre dogruluk);
resmi teslimlerde TUREF / ITRF96 TM3 secilmesi onerilir.
"""
with open(dosya("OKU_BENI.txt"), "w", encoding="utf-8") as f:
    f.write(bilgi)
kisa = f"{KOD}_{EPSG}"
ad_ = re.sub(r"[^A-Za-z0-9_-]+", "_", proje.get("ad", "proje").translate(str.maketrans("ıİşŞğĞüÜöÖçÇ", "iIsSgGuUoOcC")))[:40].strip("_")
zip_yol = os.path.join(OUT, f"BAHR_{ad_}_{kisa}.zip")
with zipfile.ZipFile(zip_yol, "w", zipfile.ZIP_DEFLATED) as zf:
    for y in sorted(set(yazilan)):
        if os.path.exists(y):
            zf.write(y, os.path.relpath(y, OUT))
with open("cozumleme/web/disari.json", "w", encoding="utf-8") as f:
    json.dump({"zip": os.path.relpath(zip_yol, "cozumleme").replace("\\", "/"), "koordinat": CRS_AD, "epsg": EPSG,
               "katmanlar": list(KATMAN.keys()), "dosya_sayisi": len(set(yazilan)), "tarih": datetime.now().isoformat(timespec="minutes")},
              f, ensure_ascii=False)
print(f"{CRS_AD} (EPSG:{EPSG}): {len(set(yazilan))} dosya -> {zip_yol}")
print("@@ilerleme 1.0", flush=True)
