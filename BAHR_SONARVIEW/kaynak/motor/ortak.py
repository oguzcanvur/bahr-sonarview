"""Motor betiklerinin ortak yardimcilari.

  parametreler()      - sunucunun proje klasorune yazdigi parametreler.json (ayarlar + proje ayarlari)
  PingOkuyucu         - bir veya birden cok RSD dosyasindan ping ornekleri okur
  koordinat_sistemi() - secili cikti koordinat sistemi (pyproj CRS) ve aciklamasi
  kaydet_png()        - Windows'ta PNG uzerine guvenli yazma
"""
import json
import math
import os

META = "cozumleme/meta/B001_ds_hifreq_meta.csv"
META_HAM = "cozumleme/meta/B001_ds_hifreq_meta_ham.csv"

VARSAYILAN = {
    "dil": "tr",
    "birim": "m",
    "kontur_araligi": 0,            # 0 = otomatik
    "renk_paleti": "viridis_r",
    "koordinat": "utm",
    "ses_hizi_modu": "kapali",      # kapali | sicaklik | elle
    "ses_hizi_elle": 1450.0,
    "cihaz_ses_hizi": 1500.0,
    "batma_payi": 0.0,              # donusturucunun su yuzeyinden derinligi (m)
    "su_kotu": 0.0,                 # tarama gunu su yuzeyi kotu (m)
    "firma_adi": "",
    "hazirlayan": "",
    "firma_logo": "",
    "degisim_proje": "",
}


def parametreler():
    p = dict(VARSAYILAN)
    if os.path.exists("parametreler.json"):
        try:
            with open("parametreler.json", encoding="utf-8") as f:
                p.update({k: v for k, v in json.load(f).items() if v is not None})
        except Exception:
            pass
    return p


def kaydet_png(fig, yol, dpi=130, **kw):
    if os.path.exists(yol):
        os.remove(yol)
    fig.savefig(yol, dpi=dpi, **kw)


class PingOkuyucu:
    """Meta satirindaki 'dosya' sutununa gore dogru RSD dosyasindan ping okur."""

    def __init__(self, kok="."):
        self.kok = kok
        self.acik = {}

    def _f(self, ad):
        if ad not in self.acik:
            self.acik[ad] = open(os.path.join(self.kok, ad), "rb")
        return self.acik[ad]

    def oku(self, r):
        if hasattr(r, "_fields"):                       # DataFrame.itertuples() satiri
            g = lambda k: getattr(r, k)                 # noqa: E731
            ad = getattr(r, "dosya", None)
        else:                                           # Series / dict
            g = lambda k: r[k]                          # noqa: E731
            ad = r.get("dosya") if hasattr(r, "get") else None
        if not isinstance(ad, str) or not ad:
            ad = "ham.RSD"
        f = self._f(ad)
        f.seek(int(g("index")) + int(g("son_offset")))
        n = int(g("ping_cnt"))
        import numpy as np
        a = np.frombuffer(f.read(n * 2), dtype="<u2")
        return a if a.size == n else None

    def kapat(self):
        for f in self.acik.values():
            f.close()
        self.acik = {}

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.kapat()


# ---------------------------------------------------------------- koordinat sistemleri
KOORDINAT_ADLARI = {
    "wgs84": "WGS84 enlem / boylam (EPSG:4326)",
    "utm": "WGS84 / UTM (6°)",
    "turef_tm3": "TUREF (ITRF96) / TM 3°",
    "ed50_tm3": "ED50 / TM 3°",
    "ed50_utm": "ED50 / UTM (6°)",
}


def koordinat_sistemi(kod, lon):
    """(pyproj.CRS, kisa ad, epsg) dondurur. lon: bolgenin boylami (dilim secimi icin)."""
    from pyproj import CRS
    if kod == "wgs84":
        epsg = 4326
    elif kod in ("turef_tm3", "ed50_tm3"):
        dm = int(min(45, max(27, 3 * round(lon / 3))))       # 27,30,...,45
        epsg = (5253 if kod == "turef_tm3" else 2319) + (dm - 27) // 3
    elif kod == "ed50_utm":
        zone = int(min(38, max(35, math.floor((lon + 180) / 6) + 1)))
        epsg = 23000 + zone
    else:
        zone = int(math.floor((lon + 180) / 6) + 1)
        epsg = 32600 + zone
    crs = CRS.from_epsg(epsg)
    return crs, crs.name, epsg


def utm_crs(lon, lat=40.0):
    from pyproj import CRS
    zone = int(math.floor((lon + 180) / 6) + 1)
    return CRS.from_epsg((32600 if lat >= 0 else 32700) + zone)


def ses_hizi_tatli_su(T):
    """Tatli suda ses hizi (m/s), Marczak (1997)."""
    return (1402.388 + 5.03711 * T - 0.0580852 * T ** 2 + 3.3420e-4 * T ** 3
            - 1.47800e-6 * T ** 4 + 3.1464e-9 * T ** 5)


def guvenilir_dip(d, en_az=1000):
    """Kisa, kopuk derinlik bolumlerini eleyen maske (diger betiklerle ayni kural)."""
    has = d["inst_dep_m"].notna()
    seg = (has.astype(int).diff() != 0).cumsum()
    return has & (has.groupby(seg).transform("sum") >= en_az)
