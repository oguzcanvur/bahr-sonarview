"""Istenen ping araliginin sonar kesitini ham RSD'den aninda uretir (PNG)."""
import io
import os
from functools import lru_cache

import numpy as np
import pandas as pd
from matplotlib import colormaps
from PIL import Image

PALETLER = {"bakir": "copper", "okyanus": "viridis", "gri": "gray", "sicak": "inferno"}


@lru_cache(maxsize=8)
def _meta(proje, mtime):
    m = pd.read_csv(os.path.join(proje, "cozumleme/meta/B001_ds_hifreq_meta.csv"),
                    usecols=["index", "son_offset", "ping_cnt", "min_range", "max_range", "inst_dep_m"])
    return m


@lru_cache(maxsize=8)
def _lut(ad):
    cm = colormaps[PALETLER.get(ad, "copper")]
    return (np.array([cm(i / 255)[:3] for i in range(256)]) * 255).astype(np.uint8)


@lru_cache(maxsize=16)
def _olcek(proje, mtime):
    """Renk olceginin alt/ust sinirlari: kaydin rastgele 300 ping'inden."""
    m = _meta(proje, mtime)
    sec = np.linspace(0, len(m) - 1, 300).astype(int)
    vals = []
    with open(os.path.join(proje, "ham.RSD"), "rb") as f:
        for i in sec:
            r = m.iloc[i]
            f.seek(int(r["index"]) + int(r["son_offset"]))
            vals.append(np.frombuffer(f.read(int(r["ping_cnt"]) * 2), "<u2"))
    v = np.concatenate(vals)
    return float(np.percentile(v, 8)), float(np.percentile(v, 99.8))


def kesit_png(proje, merkez, genislik=600, derinlik_max=4.0, yukseklik=360, palet="bakir"):
    yol = os.path.join(proje, "cozumleme/meta/B001_ds_hifreq_meta.csv")
    mt = os.path.getmtime(yol)
    m = _meta(proje, mt)
    lo, hi = _olcek(proje, mt)
    n = len(m)
    a0 = max(0, int(merkez) - genislik // 2)
    a1 = min(n, a0 + genislik)
    a0 = max(0, a1 - genislik)
    grid = np.linspace(0, derinlik_max, yukseklik)
    img = np.zeros((yukseklik, a1 - a0), np.float32)
    with open(os.path.join(proje, "ham.RSD"), "rb") as f:
        for j, i in enumerate(range(a0, a1)):
            r = m.iloc[i]
            f.seek(int(r["index"]) + int(r["son_offset"]))
            a = np.frombuffer(f.read(int(r["ping_cnt"]) * 2), "<u2").astype(np.float32)
            if a.size < 2:
                continue
            z = np.linspace(r["min_range"], r["max_range"], a.size)
            img[:, j] = np.interp(grid, z, a, right=0)
    # gama 1.6: orta tonlari koyulastirir; dip ve su ici hedefler ayrisir
    idx = (np.clip((img - lo) / max(hi - lo, 1), 0, 1) ** 1.6 * 255).astype(np.uint8)
    rgb = _lut(palet)[idx]
    rgb[img == 0] = (18, 20, 24)
    bio = io.BytesIO()
    Image.fromarray(rgb).save(bio, "PNG", optimize=False)
    dip = m["inst_dep_m"].iloc[a0:a1].to_numpy()
    return bio.getvalue(), a0, a1, [None if not np.isfinite(v) else round(float(v), 2) for v in dip]
