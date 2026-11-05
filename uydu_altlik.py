"""Ortak yardimcilar: uydu mozaigi, Mercator donusumu, harita altligi, golet su maskesi.

Once uydu.py bir kez calismis olmali (karolari indirir).
"""
import colorsys
import math
import os
from collections import deque

import numpy as np
from PIL import Image, ImageFilter

R_E = 6378137.0
ZOOM = 19
TC = "cozumleme/uydu/_karolar"
KAYNAK = "Uydu: Esri World Imagery (Esri, Maxar, Earthstar Geographics)"


def merc(lat, lon):
    lat, lon = np.asarray(lat, float), np.asarray(lon, float)
    return R_E * np.radians(lon), R_E * np.log(np.tan(np.pi / 4 + np.radians(lat) / 2))


def inv_merc(mx, my):
    return np.degrees(2 * np.arctan(np.exp(np.asarray(my) / R_E)) - np.pi / 2), np.degrees(np.asarray(mx) / R_E)


class Mozaik:
    def __init__(self):
        tiles = sorted(f for f in os.listdir(TC) if f.startswith(f"{ZOOM}_"))
        self.xs = sorted({int(f.split("_")[1]) for f in tiles})
        self.ys = sorted({int(f.split("_")[2][:-4]) for f in tiles})
        img = Image.new("RGB", (256 * len(self.xs), 256 * len(self.ys)))
        for i, x in enumerate(self.xs):
            for j, y in enumerate(self.ys):
                img.paste(Image.open(os.path.join(TC, f"{ZOOM}_{x}_{y}.jpg")).convert("RGB"), (256 * i, 256 * j))
        self.img = img
        self.A = np.asarray(img)
        size = 2 * math.pi * R_E / 2 ** ZOOM
        self.px = size / 256                                   # Mercator birimi / piksel
        self.X0 = -math.pi * R_E + self.xs[0] * size
        self.Y1 = math.pi * R_E - self.ys[0] * size
        self.ext = [self.X0, self.X0 + self.A.shape[1] * self.px, self.Y1 - self.A.shape[0] * self.px, self.Y1]

    def to_px(self, mx, my):
        return (np.asarray(mx) - self.X0) / self.px, (self.Y1 - np.asarray(my)) / self.px

    def to_merc(self, col, row):
        return self.X0 + (np.asarray(col) + 0.5) * self.px, self.Y1 - (np.asarray(row) + 0.5) * self.px

    def su_maskesi(self, tohum_mx, tohum_my):
        """Su rengindeki, tohum noktalarina (rota) bagli bolge; delikler doldurulur, kenar yumusatilir."""
        a = self.A.astype(np.float32) / 255
        hsv = np.array([colorsys.rgb_to_hsv(*p) for p in a.reshape(-1, 3)]).reshape(a.shape)
        h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
        m = (h > 0.33) & (h < 0.44) & (s > 0.22) & (s < 0.60) & (v > 0.30) & (v < 0.60)
        # kapama (kucuk bosluklari ve yansima lekelerini kapat)
        im = Image.fromarray((m * 255).astype(np.uint8))
        im = im.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.MinFilter(5))
        m = np.asarray(im) > 127
        # tohumlara bagli bileseni sec (flood fill)
        H, W = m.shape
        c, r = self.to_px(tohum_mx, tohum_my)
        c, r = c.astype(int), r.astype(int)
        ok = (r >= 0) & (r < H) & (c >= 0) & (c < W)
        seen = np.zeros_like(m)
        q = deque()
        for rr, cc in zip(r[ok], c[ok]):
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
        # delikleri doldur: kenara bagli olmayan su-disi bolgeler
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
        """Maskeyi 'metre' kadar iceri cek (k = Mercator olcek katsayisi)."""
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
        x0 = view[0] + 0.05 * (view[1] - view[0]); y0 = view[2] + 0.04 * (view[3] - view[2])
        ax.plot([x0, x0 + 20 * k], [y0, y0], color="white", lw=4, solid_capstyle="butt")
        ax.plot([x0, x0 + 20 * k], [y0, y0], color="black", lw=1.5, solid_capstyle="butt")
        ax.text(x0 + 10 * k, y0 + 2.5 * k, "20 m", color="white", ha="center", fontsize=9, weight="bold")
    ax.text(0.99, 0.005, KAYNAK, transform=ax.transAxes, ha="right", va="bottom", fontsize=6.5, color="white")
