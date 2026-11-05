"""Su kolonu onbellegi: her ping'i vericiden 3,6 m'ye kadar 2 cm'lik kutulara ozetler.

Her kutuda ornekler icinden MAKSIMUM alinir (kucuk hedefler - balik, kabarcik - kaybolmasin diye).
Cikti: cozumleme/sukolonu/_sukolonu_onbellek.npz  (wc: ping x 180, uint16; zemin.py ile ayni ping sirasi)
Kullanim:  .venv\\Scripts\\python sukolonu_onbellek.py     (~5-8 dk)
"""
import os
import numpy as np
import pandas as pd

RSD = "ham.RSD"
META = "cozumleme/meta/B001_ds_hifreq_meta.csv"
OUT = "cozumleme/sukolonu"
DZ = 0.02
os.makedirs(OUT, exist_ok=True)

d = pd.read_csv(META)
has = d["inst_dep_m"].notna()
seg = (has.astype(int).diff() != 0).cumsum()
d = d[has & (has.groupby(seg).transform("sum") >= 1000)].reset_index(drop=True)

# su kolonu: en derin noktanin biraz altina kadar (derin gollerde 30 m ile sinirli)
ZMAX = float(min(30.0, np.ceil((d["inst_dep_m"].quantile(0.995) + 0.6) / 0.2) * 0.2))
nb = int(round(ZMAX / DZ))
wc = np.zeros((len(d), nb), np.uint16)
with open(RSD, "rb") as f:
    for i, r in enumerate(d.itertuples()):
        f.seek(int(r.index) + int(r.son_offset))
        a = np.frombuffer(f.read(int(r.ping_cnt) * 2), "<u2")
        if a.size != r.ping_cnt:
            continue
        dz = r.max_range / a.size
        kut = np.minimum((np.arange(a.size) * dz / DZ).astype(int), nb)
        sel = kut < nb
        np.maximum.at(wc[i], kut[sel], a[sel])
        if i % 2000 == 0:
            print(f"@@ilerleme {i / len(d):.3f}", flush=True)
np.savez_compressed(os.path.join(OUT, "_sukolonu_onbellek.npz"), wc=wc, dz=DZ)
print("Bitti")
