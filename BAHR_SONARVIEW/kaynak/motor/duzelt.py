"""2. adim: ham meta uzerine duzeltmeleri uygular -> cozumleme/meta/B001_ds_hifreq_meta.csv

  * ses hizi duzeltmesi : derinlik ve ornek araligi (gercek / cihazin varsaydigi ses hizi) ile olceklenir
  * batma payi          : donusturucunun su yuzeyinden derinligi; derinlige ve ornek araligina eklenir
  * elle duzeltmeler    : duzeltmeler.json - silinen ping araliklari ve elle cizilen dip cizgisi
Sonraki tum adimlar duzeltilmis meta dosyasini okur.
"""
import hashlib
import json
import os

import numpy as np
import pandas as pd

from ortak import META, META_HAM, parametreler, ses_hizi_tatli_su

P = parametreler()
m = pd.read_csv(META_HAM)
if "dosya" not in m.columns:
    m["dosya"] = "ham.RSD"

# ---------------------------------------------------------------- ses hizi
cihaz = float(P.get("cihaz_ses_hizi") or 1500.0)
mod = P.get("ses_hizi_modu", "kapali")
if mod == "sicaklik":
    T = m["tempC"].where(m["tempC"].between(-2, 40)).ffill().bfill()
    T = T.fillna(T.median() if T.notna().any() else 15.0)
    carpan = ses_hizi_tatli_su(T.to_numpy()) / cihaz
elif mod == "elle":
    carpan = np.full(len(m), float(P.get("ses_hizi_elle") or cihaz) / cihaz)
else:
    carpan = np.ones(len(m))
for c in ["inst_dep_m", "min_range", "max_range"]:
    m[c] = m[c] * carpan

# ---------------------------------------------------------------- batma payi
bp = float(P.get("batma_payi") or 0.0)
if bp:
    for c in ["inst_dep_m", "min_range", "max_range"]:
        m[c] = m[c] + bp

# ---------------------------------------------------------------- elle duzeltmeler
duz = {}
if os.path.exists("duzeltmeler.json"):
    with open("duzeltmeler.json", encoding="utf-8") as f:
        duz = json.load(f)
m["elle"] = 0                                   # 0 cihaz, 1 elle cizildi, 2 silindi
n = len(m)
for d in duz.get("dip", []):
    pts = sorted((int(s), float(z)) for s, z in d.get("noktalar", []) if 0 <= int(s) < n)
    if len(pts) < 2:
        continue
    s = np.array([p[0] for p in pts])
    z = np.array([p[1] for p in pts])
    satir = np.arange(s[0], s[-1] + 1)
    m.loc[satir, "inst_dep_m"] = np.interp(satir, s, z)
    m.loc[satir, "elle"] = 1
for a0, a1 in duz.get("silinen", []):
    a0, a1 = sorted((max(0, int(a0)), min(n - 1, int(a1))))
    m.loc[a0:a1, "inst_dep_m"] = np.nan
    m.loc[a0:a1, "elle"] = 2

m.to_csv(META, index=False)

# ---------------------------------------------------------------- on bellekleri gecersiz kil
imza = hashlib.sha1(json.dumps([mod, cihaz, P.get("ses_hizi_elle"), bp, duz,
                                os.path.getmtime(META_HAM)], sort_keys=True).encode()).hexdigest()
IMZA = "cozumleme/meta/_duzelt_imza.txt"
eski = open(IMZA).read() if os.path.exists(IMZA) else None
if eski != imza:
    for c in ["cozumleme/zemin/_ping_oznitelik_onbellek.npz", "cozumleme/sukolonu/_sukolonu_onbellek.npz"]:
        if os.path.exists(c):
            os.remove(c)
    with open(IMZA, "w") as f:
        f.write(imza)

print(f"Ses hızı: {mod} (çarpan ort. {np.nanmean(carpan):.4f}), batma payı {bp:.2f} m, "
      f"elle çizilen {int((m['elle'] == 1).sum())} ping, silinen {int((m['elle'] == 2).sum())} ping")
print("@@ilerleme 1.0")
