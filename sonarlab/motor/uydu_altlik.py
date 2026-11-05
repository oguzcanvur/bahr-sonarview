"""Ortak yardimcilar: uydu mozaigi (gerekirse indirir), Mercator donusumu, harita altligi,
golet su maskesi, uyarlanir kontur seviyeleri.

Calisma klasoru = proje klasoru (cozumleme/... yollari buna gore).
"""
import colorsys
import math
import os
import urllib.request
from collections import deque

import numpy as np
from PIL import Image, ImageFilter

R_E = 6378137.0
TC = "cozumleme/uydu/_karolar"
URL = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
KAYNAK = "Uydu: Esri World Imagery (Esri, Maxar, Earthstar Geographics)"
PAY_M = 60.0          # veri alaninin cevresine eklenecek bosluk (m) - golun tamami gorunsun diye genis
MAX_KARO = 120        # mozaikte en fazla karo


def merc(lat, lon):
    lat, lon = np.asarray(lat, float), np.asarray(lon, float)
    return R_E * np.radians(lon), R_E * np.log(np.tan(np.pi / 4 + np.radians(lat) / 2))


def inv_merc(mx, my):
    return np.degrees(2 * np.arctan(np.exp(np.asarray(my) / R_E)) - np.pi / 2), np.degrees(np.asarray(mx) / R_E)


def kontur_seviyeleri(degerler, hedef=6):
    """Derinlik araligina gore 'yuvarlak' kontur seviyeleri (0.25 / 0.5 / 1 / 2 / 5 m adim)."""
    v = np.asarray(degerler, float)
    v = v[np.isfinite(v)]
    if v.size == 0:
        return np.array([1.0])
    lo, hi = np.percentile(v, 1), np.percentile(v, 99)
    for adim in (0.25, 0.5, 1.0, 2.0, 5.0, 10.0):
        if (hi - lo) / adim <= hedef:
            break
    sev = np.arange(math.ceil(lo / adim) * adim, hi + 1e-9, adim)
    return sev if sev.size else np.array([round((lo + hi) / 2, 1)])


def _tile_xy(lat, lon, z):
    n = 2 ** z
    return ((lon + 180) / 360 * n, (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n)


def _veri_siniri():
    import pandas as pd
    for yol in ("cozumleme/grafikler/ping_ozet.csv", "cozumleme/meta/B001_ds_hifreq_meta.csv"):
        if os.path.exists(yol):
            r = pd.read_csv(yol, usecols=["lat", "lon"]).dropna()
            r = r[(r["lat"].abs() > 0.01) & (r["lon"].abs() > 0.01)]
            return r["lat"].min(), r["lat"].max(), r["lon"].min(), r["lon"].max()
    raise FileNotFoundError("Konum verisi bulunamadi (once temel analiz calismali)")


def karolari_hazirla():
    """Veri alanini kapsayan karolari indirir (varsa atlar). Donus: (zoom, xs, ys) ya da indirme olmadiysa None."""
    lat0, lat1, lon0, lon1 = _veri_siniri()
    dl = PAY_M / 111320
    dlo = dl / math.cos(math.radians((lat0 + lat1) / 2))
    for z in range(19, 12, -1):
        tx0, ty0 = _tile_xy(lat1 + dl, lon0 - dlo, z)
        tx1, ty1 = _tile_xy(lat0 - dl, lon1 + dlo, z)
        xs, ys = list(range(int(tx0), int(tx1) + 1)), list(range(int(ty0), int(ty1) + 1))
        if len(xs) * len(ys) <= MAX_KARO:
            break
    os.makedirs(TC, exist_ok=True)
    for x in xs:
        for y in ys:
            fn = os.path.join(TC, f"{z}_{x}_{y}.jpg")
            if os.path.exists(fn):
                continue
            req = urllib.request.Request(URL.format(z=z, x=x, y=y), headers={"User-Agent": "SonarLab/1.0"})
            with urllib.request.urlopen(req, timeout=30) as r, open(fn, "wb") as f:
                f.write(r.read())
    return z, xs, ys


class Mozaik:
    """Uydu mozaigi. Karolar yoksa indirir; internet yoksa duz gri altlikla calisir (self.uydu=False)."""

    def __init__(self):
        self.uydu = True
        try:
            z, xs, ys = karolari_hazirla()
            imgs = {(x, y): Image.open(os.path.join(TC, f"{z}_{x}_{y}.jpg")).convert("RGB") for x in xs for y in ys}
        except Exception as e:                                 # internet yok vb.
            print("UYARI: uydu goruntusu alinamadi, duz altlik kullaniliyor:", e)
            self.uydu = False
            lat0, lat1, lon0, lon1 = _veri_siniri()
            z = 19
            while True:
                tx0, ty0 = _tile_xy(lat1, lon0, z); tx1, ty1 = _tile_xy(lat0, lon1, z)
                xs, ys = list(range(int(tx0) - 1, int(tx1) + 2)), list(range(int(ty0) - 1, int(ty1) + 2))
                if len(xs) * len(ys) <= MAX_KARO or z <= 13:
                    break
                z -= 1
            imgs = {(x, y): Image.new("RGB", (256, 256), (58, 64, 70)) for x in xs for y in ys}
        self.zoom, self.xs, self.ys = z, xs, ys
        img = Image.new("RGB", (256 * len(xs), 256 * len(ys)))
        for i, x in enumerate(xs):
            for j, y in enumerate(ys):
                img.paste(imgs[(x, y)], (256 * i, 256 * j))
        self.img = img
        self.A = np.asarray(img)
        size = 2 * math.pi * R_E / 2 ** z
        self.px = size / 256
        self.X0 = -math.pi * R_E + xs[0] * size
        self.Y1 = math.pi * R_E - ys[0] * size
        self.ext = [self.X0, self.X0 + self.A.shape[1] * self.px, self.Y1 - self.A.shape[0] * self.px, self.Y1]

    def to_px(self, mx, my):
        return (np.asarray(mx) - self.X0) / self.px, (self.Y1 - np.asarray(my)) / self.px

    def to_merc(self, col, row):
        return self.X0 + (np.asarray(col) + 0.5) * self.px, self.Y1 - (np.asarray(row) + 0.5) * self.px

    def su_maskesi(self, tohum_mx, tohum_my):
        """Su yuzeyi maskesi. Su rengi, tekne rotasinin altindaki piksellerden OGRENILIR (her gol icin),
        bu renge yakin ve rotaya bagli bolge alinir, delikler doldurulur."""
        H, W = self.A.shape[:2]
        if not self.uydu:
            return np.zeros((H, W), bool)
        a = self.A.astype(np.float32) / 255
        hsv = np.array([colorsys.rgb_to_hsv(*p) for p in a.reshape(-1, 3)]).reshape(a.shape)
        c, r = self.to_px(tohum_mx, tohum_my)
        c, r = c.astype(int), r.astype(int)
        ok = (r >= 0) & (r < H) & (c >= 0) & (c < W)
        c, r = c[ok], r[ok]
        ornek = hsv[r, c]
        med = np.median(ornek, 0)
        yay = np.maximum(np.percentile(ornek, 97, 0) - np.percentile(ornek, 3, 0), [0.03, 0.08, 0.08])
        # ton dairesel: fark min(|d|, 1-|d|)
        dh = np.abs(hsv[..., 0] - med[0]); dh = np.minimum(dh, 1 - dh)
        m = ((dh <= yay[0] * 1.2 + 0.02) & (np.abs(hsv[..., 1] - med[1]) <= yay[1] * 1.2 + 0.05)
             & (np.abs(hsv[..., 2] - med[2]) <= yay[2] * 1.2 + 0.05))
        im = Image.fromarray((m * 255).astype(np.uint8))
        im = im.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.MinFilter(5))
        m = np.asarray(im) > 127
        seen = np.zeros_like(m)
        q = deque()
        for rr, cc in zip(r, c):
            if m[rr, cc] and not seen[rr, cc]:
                seen[rr, cc] = True
                q.append((rr, cc))
        while q:
            rr, cc = q.popleft()
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                y, x = rr + dr, cc + dc
                if 0 <= y < H and 0 <= x < W and m[y, x] and not seen[y, x]:
                    seen[y, x] = True
                    q.append((y, x))
        dis = ~seen
        ulas = np.zeros_like(dis)
        q = deque([(y, x) for y in range(H) for x in (0, W - 1) if dis[y, x]] +
                  [(y, x) for x in range(W) for y in (0, H - 1) if dis[y, x]])
        for y, x in q:
            ulas[y, x] = True
        while q:
            rr, cc = q.popleft()
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                y, x = rr + dr, cc + dc
                if 0 <= y < H and 0 <= x < W and dis[y, x] and not ulas[y, x]:
                    ulas[y, x] = True
                    q.append((y, x))
        return ~ulas

    def erode(self, mask, metre, k):
        n = int(round(metre * k / self.px))
        if n < 1:
            return mask
        im = Image.fromarray((mask * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(2 * n + 1))
        return np.asarray(im) > 127


def altlik(ax, moz, view, k, baslik, olcek=True):
    ax.imshow(moz.A, extent=moz.ext, origin="upper", interpolation="bilinear")
    ax.set_xlim(view[:2]); ax.set_ylim(view[2:])
    ax.set_aspect("equal")
    ax.set_xticks([]); ax.set_yticks([])
    ax.set_title(baslik, fontsize=11)
    if olcek:
        gen = (view[1] - view[0]) / k
        uz = next(u for u in (5, 10, 20, 50, 100, 200, 500, 1000, 2000) if u >= gen / 6)
        x0 = view[0] + 0.05 * (view[1] - view[0]); y0 = view[2] + 0.04 * (view[3] - view[2])
        ax.plot([x0, x0 + uz * k], [y0, y0], color="white", lw=4, solid_capstyle="butt")
        ax.plot([x0, x0 + uz * k], [y0, y0], color="black", lw=1.5, solid_capstyle="butt")
        ax.text(x0 + uz * k / 2, y0 + 0.012 * (view[3] - view[2]), f"{uz} m", color="white", ha="center",
                fontsize=9, weight="bold")
    if moz.uydu:
        ax.text(0.99, 0.005, KAYNAK, transform=ax.transAxes, ha="right", va="bottom", fontsize=6.5, color="white")
