"""1. adim: ham.RSD dosyasini dogrula ve PINGVerter ile coz.

Cikti: cozumleme/meta/B001_*_meta.csv (ping basina metadata), DAT_meta.csv
Kanal birden fazlaysa (or. geleneksel + DownVu) en cok ping'e sahip asagi bakan kanal B001 olarak secilir.
"""
import glob
import os
import shutil
import sys

RSD = "ham.RSD"
KAYIT_BASI = b"\x86\xda\xe9\xb7"     # Garmin RSD kayit isareti (0xB7E9DA86)

if not os.path.exists(RSD):
    sys.exit("HATA: Yüklenen dosya bulunamadı")
with open(RSD, "rb") as f:
    bas = f.read(2_000_000)
if bas.count(KAYIT_BASI) < 5:
    sys.exit("HATA: Dosya Garmin RSD biçimine benzemiyor (kayıt işareti bulunamadı). "
             "Garmin cihazın hafıza kartındaki Sonar*.RSD dosyasını yükleyin.")
print("@@ilerleme 0.05", flush=True)

from pingverter import gar2pingmapper  # noqa: E402

os.makedirs("cozumleme", exist_ok=True)
g = gar2pingmapper(RSD, "cozumleme")
print("@@ilerleme 0.9", flush=True)

metas = sorted(glob.glob("cozumleme/meta/B*_meta.csv"))
metas = [m for m in metas if "All-Garmin" not in m]
if not metas:
    sys.exit("HATA: Dosyada çözülebilen sonar kanalı bulunamadı")
import pandas as pd  # noqa: E402
boy = {m: len(pd.read_csv(m, usecols=["record_num"])) for m in metas}
asagi = [m for m in metas if "ds_" in os.path.basename(m)]
sec = max(asagi or metas, key=boy.get)
hedef = "cozumleme/meta/B001_ds_hifreq_meta.csv"
if os.path.abspath(sec) != os.path.abspath(hedef):
    shutil.copy(sec, hedef)
print("Kanallar:", {os.path.basename(k): v for k, v in boy.items()}, "-> secilen:", os.path.basename(sec))
d = pd.read_csv(hedef, usecols=["inst_dep_m", "lat", "lon"])
if d["inst_dep_m"].notna().sum() < 100:
    sys.exit("HATA: Kayıtta derinlik okuması yok denecek kadar az")
if (d["lat"].abs() < 0.01).mean() > 0.5:
    sys.exit("HATA: Kayıtta GPS konumu yok; harita üretilemez")
print("@@ilerleme 1.0", flush=True)
