"""1. adim: projedeki RSD kayit(lar)ini dogrula, PINGVerter ile coz ve birlestir.

Cikti: cozumleme/meta/B001_ds_hifreq_meta_ham.csv  (tum kayitlar, zaman sirasinda; 'dosya' sutunu
       hangi RSD dosyasindan geldigini gosterir), DAT_meta.csv
Kayitlar degismediyse cozme atlanir (ayar degisikliginden sonra yeniden hesaplama hizli olsun diye).
Duzeltmeler (ses hizi, batma payi, elle duzeltme) sonraki adimda duzelt.py ile uygulanir.
"""
import glob
import json
import os
import shutil
import sys

import pandas as pd

from ortak import META, META_HAM

KAYIT_BASI = b"\x86\xda\xe9\xb7"     # Garmin RSD kayit isareti (0xB7E9DA86)


def kayit_listesi():
    try:
        with open("proje.json", encoding="utf-8") as f:
            v = json.load(f)
        k = [x["dosya"] for x in v.get("kayitlar", []) if x.get("dosya")]
        if k:
            return k
    except Exception:
        pass
    return ["ham.RSD"]


def dogrula(yol, ad):
    if not os.path.exists(yol):
        sys.exit(f"HATA: Kayıt dosyası bulunamadı ({ad})")
    with open(yol, "rb") as f:
        bas = f.read(2_000_000)
    if bas.count(KAYIT_BASI) < 5:
        sys.exit(f"HATA: '{ad}' Garmin RSD biçiminde değil ya da bozuk (kayıt işareti bulunamadı). "
                 "Garmin cihazın hafıza kartındaki Sonar*.RSD dosyasını yükleyin.")


def kanal_sec(klasor):
    metas = [m for m in sorted(glob.glob(os.path.join(klasor, "meta", "B*_meta.csv"))) if "All-Garmin" not in m]
    if not metas:
        return None, {}
    boy = {m: len(pd.read_csv(m, usecols=["record_num"])) for m in metas}
    asagi = [m for m in metas if "ds_" in os.path.basename(m)]
    return max(asagi or metas, key=boy.get), boy


kayitlar = kayit_listesi()
imza = [[k, os.path.getsize(k) if os.path.exists(k) else 0] for k in kayitlar]
IMZA = "cozumleme/meta/_kayitlar.json"
os.makedirs("cozumleme/meta", exist_ok=True)


def imza_oku():
    try:
        with open(IMZA, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


if imza_oku() == imza and os.path.exists(META_HAM):
    print("Kayıtlar değişmedi; çözme atlandı")
    print("@@ilerleme 1.0", flush=True)
    sys.exit(0)

# eski surumle cozulmus tek kayitli proje: yeniden cozmeden ham meta olustur
if kayitlar == ["ham.RSD"] and os.path.exists(META) and not os.path.exists(META_HAM) and imza_oku() is None:
    d = pd.read_csv(META)
    if "dosya" not in d.columns:
        d["dosya"] = "ham.RSD"
    d.to_csv(META_HAM, index=False)
    with open(IMZA, "w", encoding="utf-8") as f:
        json.dump(imza, f)
    print("Önceki çözümleme kullanıldı")
    print("@@ilerleme 1.0", flush=True)
    sys.exit(0)

for k in kayitlar:
    dogrula(k, k)
print("@@ilerleme 0.03", flush=True)

from pingverter import gar2pingmapper  # noqa: E402

parcalar = []
for i, k in enumerate(kayitlar):
    klasor = f"cozumleme/_kayit{i + 1}"
    shutil.rmtree(klasor, ignore_errors=True)
    try:
        gar2pingmapper(k, klasor)
    except Exception as e:  # noqa: BLE001
        sys.exit(f"HATA: '{k}' çözülemedi; dosya bozuk ya da desteklenmeyen bir Garmin sürümü olabilir ({type(e).__name__}).")
    sec, boy = kanal_sec(klasor)
    if sec is None:
        sys.exit(f"HATA: '{k}' içinde çözülebilen sonar kanalı bulunamadı")
    print(f"{k}: kanallar", {os.path.basename(a): b for a, b in boy.items()}, "-> seçilen:", os.path.basename(sec))
    d = pd.read_csv(sec)
    d["dosya"] = k
    if i == 0 and os.path.exists(os.path.join(klasor, "meta", "DAT_meta.csv")):
        shutil.copy(os.path.join(klasor, "meta", "DAT_meta.csv"), "cozumleme/meta/DAT_meta.csv")
    parcalar.append(d)
    print(f"@@ilerleme {0.05 + 0.85 * (i + 1) / len(kayitlar):.3f}", flush=True)

# birlestir: zaman sirasina diz, sure ve yol sutunlarini kesintisiz yap
for d in parcalar:
    d["_dt"] = pd.to_datetime(d["date"] + " " + d["time"], format="ISO8601", errors="coerce")
parcalar.sort(key=lambda d: d["_dt"].min())
yol_ofset = 0.0
for d in parcalar:
    if "trk_dist" in d:
        d["trk_dist"] = d["trk_dist"] + yol_ofset
        yol_ofset = float(d["trk_dist"].max())
m = pd.concat(parcalar, ignore_index=True)
t0 = m["_dt"].min()
if len(parcalar) > 1:
    m["time_s"] = (m["_dt"] - t0).dt.total_seconds()
m = m.drop(columns=["_dt"])
m.to_csv(META_HAM, index=False)
with open(IMZA, "w", encoding="utf-8") as f:
    json.dump(imza, f)
# eski on bellekler yeni kayit setiyle uyusmaz
for c in ["cozumleme/zemin/_ping_oznitelik_onbellek.npz", "cozumleme/sukolonu/_sukolonu_onbellek.npz"]:
    if os.path.exists(c):
        os.remove(c)

if m["inst_dep_m"].notna().sum() < 100:
    sys.exit("HATA: Kayıtta derinlik okuması yok denecek kadar az; cihaz kayıt sırasında dibi görmemiş olabilir")
if (m["lat"].abs() < 0.01).mean() > 0.5:
    sys.exit("HATA: Kayıtta GPS konumu yok; harita üretilemez. Cihazın GPS'i açıkken kaydedilmiş bir dosya yükleyin")
print(f"{len(kayitlar)} kayıt, {len(m)} ping birleştirildi")
print("@@ilerleme 1.0", flush=True)
