"""BAHR SONARVIEW - yerel sunucu (arayuz, ayarlar, analiz kuyrugu, guncelleme).

Hem gelistirme ortaminda (python bahr_sonarview.py) hem de PyInstaller ile
paketlenmis .exe icinde calisir.
"""
import io
import json
import math
import os
import platform
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
import uuid
import zipfile
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

import surum

DONDURULMUS = getattr(sys, "frozen", False)
# kaynaklar (salt okunur): .exe icinde _MEIPASS, gelistirmede bu klasor
KAYNAK = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
MOTOR = KAYNAK / "motor"
STATIK = KAYNAK / "static"
# veriler (yazilabilir): .exe'nin yaninda, gelistirmede BAHR_SONARVIEW/Projeler
UYGULAMA_KOK = Path(sys.executable).resolve().parent if DONDURULMUS else Path(__file__).resolve().parent.parent
PROJELER = UYGULAMA_KOK / "Projeler"
PROJELER.mkdir(exist_ok=True)
AYAR_DOSYASI = UYGULAMA_KOK / "ayarlar.json"
sys.path.insert(0, str(MOTOR))
from kesit import kesit_png  # noqa: E402
from ortak import KOORDINAT_ADLARI, VARSAYILAN  # noqa: E402

ANALIZLER = {
    "temel": {"ad": "Temel analiz", "gerekir": [], "adimlar": [
        ("cozumle.py", [], "Dosya çözülüyor", 2),
        ("duzelt.py", [], "Düzeltmeler uygulanıyor", 0.4),
        ("analiz.py", [], "Sonar görüntüleri ve grafikler", 3),
        ("kontur.py", [], "Derinlik haritası", 1),
        ("izgara.py", [], "Derinlik ızgarası", 0.5),
        ("katmanlar.py", ["temel"], "Harita katmanları", 1),
        ("yuzey_analizi.py", [], "Hacim tablosu ve belirsizlik", 0.6)]},
    "zemin": {"ad": "Zemin sınıflaması", "gerekir": ["temel"], "adimlar": [
        ("zemin.py", [], "Dip yankıları inceleniyor", 10),
        ("numune.py", [], "Numune noktaları seçiliyor", 1),
        ("katmanlar.py", ["zemin"], "Harita katmanları", 1)]},
    "uydu": {"ad": "Uydu, hacim ve rota", "gerekir": ["temel"], "adimlar": [
        ("uydu.py", [], "Uydu görüntüsü", 2),
        ("morfoloji.py", [], "Hacim, eğim, kapsama, rota", 3),
        ("katmanlar.py", ["uydu"], "Harita katmanları", 1),
        ("yuzey_analizi.py", [], "Hacim tablosu ve belirsizlik", 0.6)]},
    "taramalar": {"ad": "Su kolonu ve dip taramaları", "gerekir": ["temel", "zemin"], "adimlar": [
        ("sukolonu_onbellek.py", [], "Su kolonu okunuyor", 5),
        ("sertnokta.py", [], "Kaya / nesne taraması", 1),
        ("bitki.py", [], "Bitki örtüsü taraması", 3),
        ("balik.py", [], "Balık ve kabarcık taraması", 3),
        ("katmanlar.py", ["taramalar"], "Harita katmanları", 1)]},
    "dogrulama": {"ad": "Doğrulama ve kalibrasyon", "gerekir": ["temel"], "adimlar": [
        ("dogrulama.py", [], "Saha verisiyle karşılaştırılıyor", 1)]},
    "degisim": {"ad": "Değişim analizi", "gerekir": ["temel"], "adimlar": [
        ("degisim.py", [], "Taramalar karşılaştırılıyor", 1)]},
    "disari": {"ad": "Mühendislik çıktıları", "gerekir": ["temel"], "adimlar": [
        ("disari.py", [], "GeoTIFF, Shapefile, KML, DXF hazırlanıyor", 1)]},
    "rapor": {"ad": "Rapor", "gerekir": ["temel"], "adimlar": [
        ("rapor.py", [], "Rapor hazırlanıyor", 1),
        ("pdf.py", [], "PDF oluşturuluyor", 1)]},
}
SIRA = ["temel", "zemin", "uydu", "taramalar", "dogrulama", "degisim", "disari", "rapor"]
PROJE_PARAMETRELERI = ["ses_hizi_modu", "ses_hizi_elle", "cihaz_ses_hizi", "batma_payi", "su_kotu", "degisim_proje"]
GENEL_AYARLAR = ["dil", "birim", "kontur_araligi", "renk_paleti", "koordinat", "firma_adi", "hazirlayan", "firma_logo",
                 "guncelleme_denetle", "ses_hizi_modu", "ses_hizi_elle", "cihaz_ses_hizi", "batma_payi"]
PALETLER = ["viridis_r", "Blues", "ocean_r", "cividis_r", "plasma_r", "YlGnBu", "turbo_r", "terrain_r"]

kilit = threading.Lock()
is_kuyrugu: "queue.Queue[tuple[str, str, str]]" = queue.Queue()
calisan_surecler: set = set()
aktif = {"pid": None, "tur": None, "p": None, "iptal": False}


class KullaniciHatasi(Exception):
    """Kullaniciya oldugu gibi gosterilecek, anlasilir hata."""


# ---------------------------------------------------------------- ayarlar
def ayarlar() -> dict:
    a = {k: VARSAYILAN.get(k) for k in GENEL_AYARLAR}
    a["guncelleme_denetle"] = True
    if AYAR_DOSYASI.exists():
        try:
            a.update({k: v for k, v in json.loads(AYAR_DOSYASI.read_text(encoding="utf-8")).items() if k in GENEL_AYARLAR})
        except Exception:
            pass
    return a


def ayar_yaz(yeni: dict) -> dict:
    a = ayarlar()
    for k, v in yeni.items():
        if k in GENEL_AYARLAR:
            a[k] = v
    a = ayar_dogrula(a)
    AYAR_DOSYASI.write_text(json.dumps(a, ensure_ascii=False, indent=1), encoding="utf-8")
    return a


def sayi_al(v, vars_, lo, hi):
    try:
        f = float(str(v).replace(",", "."))
        return min(hi, max(lo, f)) if math.isfinite(f) else vars_
    except Exception:
        return vars_


def ayar_dogrula(a: dict) -> dict:
    if "dil" in a and a["dil"] not in ("tr", "en"):
        a["dil"] = "tr"
    if "birim" in a and a["birim"] not in ("m", "ft"):
        a["birim"] = "m"
    if "koordinat" in a and a["koordinat"] not in KOORDINAT_ADLARI:
        a["koordinat"] = "utm"
    if "renk_paleti" in a and a["renk_paleti"] not in PALETLER:
        a["renk_paleti"] = "viridis_r"
    if "ses_hizi_modu" in a and a["ses_hizi_modu"] not in ("kapali", "sicaklik", "elle"):
        a["ses_hizi_modu"] = "kapali"
    for k, (vv, lo, hi) in {"kontur_araligi": (0, 0, 50), "ses_hizi_elle": (1450, 1300, 1700), "cihaz_ses_hizi": (1500, 1300, 1700),
                            "batma_payi": (0, -2, 5), "su_kotu": (0, -500, 9000)}.items():
        if k in a:
            a[k] = sayi_al(a[k], vv, lo, hi)
    for k in ("firma_adi", "hazirlayan", "degisim_proje"):
        if k in a:
            a[k] = str(a[k] or "")[:160]
    return a


def proje_parametreleri(v: dict) -> dict:
    """Varsayilan <- genel ayarlar <- proje ayarlari."""
    p = dict(VARSAYILAN)
    p.update(ayarlar())
    p.update({k: x for k, x in (v.get("parametreler") or {}).items() if x is not None})
    return p


def parametre_dosyasi_yaz(pid: str):
    p = proje_parametreleri(oku(pid))
    (PROJELER / pid / "parametreler.json").write_text(json.dumps(p, ensure_ascii=False, indent=1), encoding="utf-8")


# ---------------------------------------------------------------- proje kaydi
def pdir(pid: str) -> Path:
    p = (PROJELER / pid).resolve()
    if p.parent != PROJELER.resolve() or not (p / "proje.json").exists():
        raise HTTPException(404, "Proje bulunamadı")
    return p


def oku(pid: str) -> dict:
    with open(PROJELER / pid / "proje.json", encoding="utf-8") as f:
        v = json.load(f)
    if not v.get("kayitlar"):
        v["kayitlar"] = [{"dosya": "ham.RSD", "ad": v.get("dosya_adi", "ham.RSD"), "boyut": v.get("boyut", 0)}]
    v.setdefault("parametreler", {})
    v["id"] = pid                                     # klasor adi esastir (kopyalanan projeler icin)
    return v


def yaz(pid: str, veri: dict):
    tmp = PROJELER / pid / "proje.json.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=1)
    # Windows'ta dosya o an okunuyorsa (arayuz yoklamasi) yeniden adlandirma
    # "Erisim engellendi" verir; kisa beklemelerle yeniden dene.
    for deneme in range(20):
        try:
            os.replace(tmp, PROJELER / pid / "proje.json")
            return
        except PermissionError:
            if deneme == 19:
                raise
            time.sleep(0.05)


def guncelle(pid: str, tur: str, **alanlar):
    with kilit:
        v = oku(pid)
        v["analizler"].setdefault(tur, {}).update(alanlar)
        yaz(pid, v)


def proje_degistir(pid: str, f):
    with kilit:
        v = oku(pid)
        f(v)
        yaz(pid, v)
        return v


def motor_komutu(betik: str, args: list) -> list:
    if DONDURULMUS:                                   # .exe kendini motor kipinde cagirir
        return [sys.executable, "--motor", betik, *args]
    return [sys.executable, "-u", str(MOTOR / betik), *args]


MOTOR_ORTAM = dict(PYTHONPATH=str(MOTOR), PYTHONIOENCODING="utf-8", MPLBACKEND="Agg", PYTHONWARNINGS="ignore", PYTHONUNBUFFERED="1")


def surec_agacini_bitir(p):
    try:
        subprocess.run(["taskkill", "/PID", str(p.pid), "/T", "/F"], capture_output=True,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), timeout=15)
    except Exception:
        try:
            p.kill()
        except Exception:
            pass


# ---------------------------------------------------------------- anlasilir hata mesajlari
def anlasilir_hata(etiket: str, satirlar: list) -> tuple[str, str]:
    teknik = next((s for s in reversed(satirlar) if s.startswith("HATA")), None) or (satirlar[-1] if satirlar else "")
    metin = "\n".join(satirlar[-12:])
    if teknik.startswith("HATA:"):
        return teknik[5:].strip(), teknik
    if "MemoryError" in metin or "Unable to allocate" in metin:
        return ("Bilgisayarın belleği bu kayıt için yetmedi. Diğer programları kapatıp tekrar deneyin; "
                "çok uzun kayıtları cihazda bölerek kaydetmek de işe yarar."), teknik
    if any(s in metin for s in ("URLError", "getaddrinfo", "timed out", "ConnectionError", "HTTPError", "RemoteDisconnected")):
        return "İnternet bağlantısı gerekli: uydu görüntüsü indirilemedi. Bağlantınızı kontrol edip tekrar deneyin.", teknik
    if "PermissionError" in metin or "Errno 13" in metin:
        return "Bir çıktı dosyası başka bir programda açık olduğu için yazılamadı. Açık görsel / Excel dosyalarını kapatıp tekrar deneyin.", teknik
    if "No space left" in metin or "Errno 28" in metin:
        return "Diskte yer kalmadı. Yer açıp tekrar deneyin.", teknik
    return (f"'{etiket}' adımında beklenmeyen bir hata oluştu. Ayrıntılar analiz günlüğüne yazıldı; "
            "üstteki menüden 'Hata raporu oluştur' ile paylaşabilirsiniz."), teknik


# ---------------------------------------------------------------- is calistirici
def calistir(pid: str, tur: str):
    adimlar = ANALIZLER[tur]["adimlar"]
    toplam = sum(a[3] for a in adimlar)
    yapilan = 0
    t0 = time.time()
    parametre_dosyasi_yaz(pid)
    guncelle(pid, tur, durum="calisiyor", ilerleme=0.0, adim=adimlar[0][2], mesaj=None, teknik=None, baslangic=t0)
    env = dict(os.environ, **MOTOR_ORTAM)
    for betik, args, etiket, agirlik in adimlar:
        guncelle(pid, tur, adim=etiket)
        p = subprocess.Popen(motor_komutu(betik, args), cwd=PROJELER / pid, stdin=subprocess.DEVNULL,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                             errors="replace", env=env, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        calisan_surecler.add(p)
        with kilit:
            aktif.update(pid=pid, tur=tur, p=p)
        son, son_yazim = [], 0.0
        try:
            for satir in p.stdout:
                satir = satir.rstrip()
                if satir.startswith("@@ilerleme"):
                    try:
                        f = float(satir.split()[1])
                        if time.time() - son_yazim > 0.7:
                            guncelle(pid, tur, ilerleme=round((yapilan + agirlik * f) / toplam, 3))
                            son_yazim = time.time()
                    except ValueError:
                        pass
                    continue
                if satir:
                    son = (son + [satir])[-60:]
            p.wait()
        finally:
            calisan_surecler.discard(p)
            with kilit:
                iptal = aktif["iptal"]
                aktif.update(pid=None, tur=None, p=None, iptal=False)
        with open(PROJELER / pid / "analiz_gunlugu.txt", "a", encoding="utf-8") as g:
            g.write(f"\n=== {datetime.now():%Y-%m-%d %H:%M:%S} {tur} / {betik} (cikis {p.returncode})\n" + "\n".join(son) + "\n")
        if iptal:
            guncelle(pid, tur, durum="iptal", mesaj="İptal edildi", adim=None, bitis=time.time())
            return
        if p.returncode != 0:
            mesaj, teknik = anlasilir_hata(etiket, son)
            guncelle(pid, tur, durum="hata", mesaj=mesaj[:600], teknik=teknik[:600], adim=None, bitis=time.time())
            return
        yapilan += agirlik
        guncelle(pid, tur, ilerleme=round(yapilan / toplam, 3))
    guncelle(pid, tur, durum="bitti", ilerleme=1.0, adim=None, bitis=time.time(), sure_s=round(time.time() - t0))
    if tur == "temel":
        proje_degistir(pid, lambda v: v.pop("guncel_degil", None))


def isci():
    while True:
        pid, tur, jeton = is_kuyrugu.get()
        try:
            if (PROJELER / pid / "proje.json").exists():
                a = oku(pid)["analizler"].get(tur, {})
                if a.get("durum") == "bekliyor" and a.get("jeton") == jeton:     # iptal edilmis ya da eskimis is degilse
                    calistir(pid, tur)
        except Exception as e:  # noqa: BLE001
            try:
                guncelle(pid, tur, durum="hata", mesaj="Beklenmeyen hata; ayrıntı analiz günlüğünde.", teknik=str(e)[:600])
            except Exception:
                pass
        finally:
            is_kuyrugu.task_done()


def kuyruga_ekle(pid: str, tur: str, sessiz=False):
    v = oku(pid)
    for g in ANALIZLER[tur]["gerekir"]:
        if v["analizler"].get(g, {}).get("durum") not in ("bitti", "bekliyor", "calisiyor"):
            if sessiz:
                return
            raise HTTPException(409, f"Önce '{ANALIZLER[g]['ad']}' çalıştırılmalı")
    if v["analizler"].get(tur, {}).get("durum") in ("bekliyor", "calisiyor"):
        return
    jeton = uuid.uuid4().hex[:8]
    guncelle(pid, tur, durum="bekliyor", ilerleme=0.0, mesaj=None, teknik=None, adim=None, jeton=jeton)
    is_kuyrugu.put((pid, tur, jeton))


def analiz_iptal(pid: str, tur: str):
    with kilit:
        calisiyor = aktif["pid"] == pid and aktif["tur"] == tur and aktif["p"] is not None
        if calisiyor:
            aktif["iptal"] = True
            p = aktif["p"]
    if calisiyor:
        surec_agacini_bitir(p)
        return
    if oku(pid)["analizler"].get(tur, {}).get("durum") == "bekliyor":
        guncelle(pid, tur, durum="iptal", mesaj="İptal edildi", jeton=None)


def yeniden_hesapla(pid: str):
    v = oku(pid)
    yapilacak = ["temel"] + [t for t in SIRA[1:] if v["analizler"].get(t, {}).get("durum") in ("bitti", "hata", "iptal")]
    for t in yapilacak:
        if t == "degisim" and not proje_parametreleri(v).get("degisim_proje"):
            continue
        if t == "dogrulama" and not (PROJELER / pid / "dogrulama.csv").exists():
            continue
        kuyruga_ekle(pid, t, sessiz=True)
    return yapilacak


# ---------------------------------------------------------------- kayit dosyalari
KAYIT_BASI = b"\x86\xda\xe9\xb7"


def rsd_dogrula(yol: Path, ad: str):
    if yol.stat().st_size < 10_000:
        raise KullaniciHatasi(f"'{ad}' çok küçük; boş ya da yarım kopyalanmış bir dosya olabilir.")
    with open(yol, "rb") as f:
        bas = f.read(2_000_000)
    if bas.count(KAYIT_BASI) < 5:
        raise KullaniciHatasi(f"'{ad}' bir Garmin sonar kaydı (.RSD) gibi görünmüyor ya da bozuk. "
                              "Cihazın hafıza kartındaki Sonar*.RSD dosyasını seçin.")


def proje_kaydi_olustur() -> tuple[str, Path]:
    pid = datetime.now().strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:4]
    d = PROJELER / pid
    d.mkdir()
    return pid, d


def proje_bitir(pid: str, d: Path, dosya_adi: str, ad: str) -> dict:
    a = ayarlar()
    v = {"id": pid, "ad": ad.strip() or Path(dosya_adi).stem, "dosya_adi": dosya_adi,
         "boyut": (d / "ham.RSD").stat().st_size, "olusturma": time.time(), "analizler": {},
         "kayitlar": [{"dosya": "ham.RSD", "ad": dosya_adi, "boyut": (d / "ham.RSD").stat().st_size, "eklenme": time.time()}],
         "parametreler": {k: a.get(k) for k in ("ses_hizi_modu", "ses_hizi_elle", "cihaz_ses_hizi", "batma_payi")}}
    v["parametreler"]["su_kotu"] = 0.0
    yaz(pid, v)
    kuyruga_ekle(pid, "temel")
    return oku(pid)


def proje_yoldan(yol: str) -> dict:
    """Masaustu: bilgisayardaki .RSD dosyasini (HTTP yuklemesi olmadan) projeye kopyalar."""
    kaynak = Path(yol)
    if kaynak.suffix.lower() != ".rsd" or not kaynak.is_file():
        raise KullaniciHatasi("Yalnızca Garmin .RSD dosyaları destekleniyor")
    rsd_dogrula(kaynak, kaynak.name)
    pid, d = proje_kaydi_olustur()
    shutil.copyfile(kaynak, d / "ham.RSD")
    return proje_bitir(pid, d, kaynak.name, kaynak.stem)


def kayit_ekle(pid: str, kaynak: Path, ad: str, tasi=False) -> dict:
    d = pdir(pid)
    v = oku(pid)
    if any(a.get("durum") in ("bekliyor", "calisiyor") for a in v["analizler"].values()):
        raise KullaniciHatasi("Çalışan analiz varken kayıt eklenemez; bitmesini bekleyin ya da iptal edin.")
    rsd_dogrula(kaynak, ad)
    i = 2
    while (d / f"ham_{i}.RSD").exists():
        i += 1
    hedef = d / f"ham_{i}.RSD"
    (shutil.move if tasi else shutil.copyfile)(str(kaynak), str(hedef))

    def f(v):
        v["kayitlar"].append({"dosya": hedef.name, "ad": ad, "boyut": hedef.stat().st_size, "eklenme": time.time()})
        v["boyut"] = sum(k.get("boyut", 0) for k in v["kayitlar"])
        v["guncel_degil"] = True
    proje_degistir(pid, f)
    if (d / "duzeltmeler.json").exists():                 # ping sirasi degisti: elle duzeltmeler gecersiz
        (d / "duzeltmeler.json").replace(d / "duzeltmeler_eski.json")
    yeniden_hesapla(pid)
    return oku(pid)


def kayit_cikar(pid: str, dosya: str) -> dict:
    d = pdir(pid)
    v = oku(pid)
    if any(a.get("durum") in ("bekliyor", "calisiyor") for a in v["analizler"].values()):
        raise KullaniciHatasi("Çalışan analiz varken kayıt çıkarılamaz.")
    if len(v["kayitlar"]) <= 1:
        raise KullaniciHatasi("Projede en az bir kayıt kalmalı.")
    if dosya not in [k["dosya"] for k in v["kayitlar"]]:
        raise HTTPException(404, "Kayıt bulunamadı")

    def f(v):
        v["kayitlar"] = [k for k in v["kayitlar"] if k["dosya"] != dosya]
        v["boyut"] = sum(k.get("boyut", 0) for k in v["kayitlar"])
        v["guncel_degil"] = True
    proje_degistir(pid, f)
    try:
        (d / dosya).unlink()
    except OSError:
        pass
    if (d / "duzeltmeler.json").exists():
        (d / "duzeltmeler.json").replace(d / "duzeltmeler_eski.json")
    yeniden_hesapla(pid)
    return oku(pid)


def kapat():
    for p in list(calisan_surecler):
        surec_agacini_bitir(p)


# ---------------------------------------------------------------- hata raporu
def hata_raporu(pid: str | None) -> bytes:
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("sistem.txt", "\n".join([
            f"{surum.AD} {surum.SURUM}", f"Tarih: {datetime.now():%Y-%m-%d %H:%M:%S}",
            f"Windows: {platform.platform()}", f"Python: {sys.version.split()[0]}", f"Paketli: {DONDURULMUS}",
            f"İşlemci: {platform.processor()}", f"Proje sayısı: {sum(1 for p in PROJELER.iterdir() if (p / 'proje.json').exists())}"]))
        for ad in ("program_gunlugu.txt", "hata_gunlugu.txt", "ayarlar.json"):
            if (UYGULAMA_KOK / ad).exists():
                z.write(UYGULAMA_KOK / ad, ad)
        if pid:
            d = PROJELER / pid
            for ad in ("proje.json", "parametreler.json", "analiz_gunlugu.txt", "duzeltmeler.json", "cozumleme/web/ozet.json",
                       "cozumleme/meta/DAT_meta.csv", "cozumleme/meta/_kayitlar.json"):
                if (d / ad).exists():
                    z.write(d / ad, f"proje/{ad}")
        z.writestr("OKU_BENI.txt", "Bu zip hata ayıklama için günlükleri ve ayarları içerir. Sonar kaydının kendisi (RSD) ve konum "
                   "içeren çıktılar eklenmez; ancak proje özeti kaydın tarihini ve göletin yaklaşık merkezini içerebilir.")
    return b.getvalue()


# ---------------------------------------------------------------- guncelleme
GUNCEL = {"zaman": 0, "veri": None}
INDIRME = {"durum": "yok", "yuzde": 0, "hata": None, "yol": None}
GDIR = UYGULAMA_KOK / "_guncelleme"


def surum_demeti(s: str):
    try:
        return tuple(int(x) for x in str(s).lstrip("vV").split(".")[:3])
    except Exception:
        return (0,)


def guncelleme_denetle(zorla=False) -> dict:
    if not zorla and GUNCEL["veri"] and time.time() - GUNCEL["zaman"] < 6 * 3600:
        return GUNCEL["veri"]
    istek = urllib.request.Request(f"https://api.github.com/repos/{surum.DEPO}/releases/latest",
                                   headers={"User-Agent": f"BAHR-SONARVIEW/{surum.SURUM}", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(istek, timeout=8) as r:
        j = json.loads(r.read().decode("utf-8"))
    paket = next((a for a in j.get("assets", []) if a.get("name", "").lower().endswith(".zip")), None)
    son = str(j.get("tag_name", "")).lstrip("vV")
    veri = {"mevcut": surum.SURUM, "son": son, "yeni_var": surum_demeti(son) > surum_demeti(surum.SURUM),
            "notlar": (j.get("body") or "")[:4000], "sayfa": j.get("html_url"), "tarih": (j.get("published_at") or "")[:10],
            "indirme": paket.get("browser_download_url") if paket else None, "boyut": paket.get("size") if paket else None,
            "kurulabilir": DONDURULMUS and bool(paket)}
    GUNCEL.update(zaman=time.time(), veri=veri)
    return veri


def guncelleme_indir():
    v = GUNCEL["veri"]
    if not v or not v.get("indirme"):
        raise KullaniciHatasi("İndirilecek güncelleme bulunamadı")
    if INDIRME["durum"] == "iniyor":
        return

    def is_():
        try:
            GDIR.mkdir(exist_ok=True)
            yol = GDIR / "paket.zip"
            INDIRME.update(durum="iniyor", yuzde=0, hata=None, yol=None)
            istek = urllib.request.Request(v["indirme"], headers={"User-Agent": f"BAHR-SONARVIEW/{surum.SURUM}"})
            with urllib.request.urlopen(istek, timeout=30) as r, open(yol, "wb") as f:
                toplam = int(r.headers.get("Content-Length") or v.get("boyut") or 0)
                inen = 0
                while True:
                    parca = r.read(1 << 20)
                    if not parca:
                        break
                    f.write(parca)
                    inen += len(parca)
                    INDIRME["yuzde"] = round(100 * inen / toplam, 1) if toplam else 0
            with zipfile.ZipFile(yol) as z:
                if z.testzip() is not None:
                    raise ValueError("indirilen paket bozuk")
            INDIRME.update(durum="hazir", yuzde=100, yol=str(yol))
        except Exception as e:  # noqa: BLE001
            INDIRME.update(durum="hata", hata=f"İndirme başarısız: {e}")
    threading.Thread(target=is_, daemon=True).start()


def guncelleme_kur() -> dict:
    """Paketi acar ve program kapaninca dosyalari degistirip yeniden baslatan betigi hazirlar."""
    if not DONDURULMUS:
        raise KullaniciHatasi("Otomatik kurulum yalnızca paketlenmiş programda yapılabilir.")
    if INDIRME["durum"] != "hazir":
        raise KullaniciHatasi("Önce güncellemeyi indirin.")
    acik = GDIR / "acik"
    shutil.rmtree(acik, ignore_errors=True)
    with zipfile.ZipFile(INDIRME["yol"]) as z:
        z.extractall(acik)
    exe = next(acik.rglob("BAHR SONARVIEW.exe"), None)
    if exe is None:
        raise KullaniciHatasi("Güncelleme paketi beklenen yapıda değil.")
    yeni = exe.parent
    hedef = UYGULAMA_KOK
    bat = GDIR / "guncelle.bat"
    bat.write_text(f"""@echo off
chcp 65001 >nul
:bekle
tasklist /FI "PID eq {os.getpid()}" | find "{os.getpid()}" >nul && (timeout /t 1 /nobreak >nul & goto bekle)
robocopy "{yeni}" "{hedef}" /E /XD Projeler .pencere _guncelleme /XF ayarlar.json firma_logo.png /NFL /NDL /NJH /NJS /NP >nul
start "" "{hedef / 'BAHR SONARVIEW.exe'}"
""", encoding="utf-8")
    subprocess.Popen(["cmd", "/c", str(bat)], cwd=str(GDIR),
                     creationflags=getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
                     | getattr(subprocess, "CREATE_NO_WINDOW", 0))
    return {"tamam": True}


# ---------------------------------------------------------------- izgara onbellegi, profil, 3B yuzey
_izgara_onbellek = {}


def _raster_nokta(x, y, v, h=1.0, kategorik=False):
    """Duzensiz noktalari h boyutlu UTM izgarasina yerlestirir; kucuk bosluklari komsulardan doldurur."""
    import numpy as np
    X0 = math.floor(x.min() / h) * h - h
    Y1 = math.ceil(y.max() / h) * h + h
    W, H = int((x.max() - X0) / h) + 3, int((Y1 - y.min()) / h) + 3
    A = np.full((H, W), np.nan, np.float32)
    A[np.clip(((Y1 - y) / h).astype(int), 0, H - 1), np.clip(((x - X0) / h).astype(int), 0, W - 1)] = v
    for _ in range(2):                                   # izgaralar arasi kucuk kaymalardan dogan delikler
        bos = ~np.isfinite(A)
        n = np.zeros(A.shape, np.float32)
        t = np.zeros(A.shape, np.float32)
        ilk = np.full(A.shape, np.nan, np.float32)
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            k = np.roll(A, (dy, dx), (0, 1))
            g = np.isfinite(k)
            n += g
            t += np.where(g, k, 0)
            ilk = np.where(~np.isfinite(ilk) & g, k, ilk)
        dol = bos & (n >= 3)
        A[dol] = (ilk if kategorik else t / np.maximum(n, 1))[dol]
    return {"a": A, "x0": X0, "y1": Y1, "h": h}


def _ornek(R, x, y):
    import numpy as np
    a = R["a"]
    c = np.floor((x - R["x0"]) / R["h"]).astype(int)
    r = np.floor((R["y1"] - y) / R["h"]).astype(int)
    ok = (c >= 0) & (c < a.shape[1]) & (r >= 0) & (r < a.shape[0])
    out = np.full(x.shape, np.nan, np.float32)
    out[ok] = a[r[ok], c[ok]]
    return out


def izgara_yukle(pid: str) -> dict:
    """Projenin olculen derinlik izgarasi (Z), uydu tahmini (T) ve zemin sinifi (S); degisince yeniden okunur."""
    import numpy as np
    import pandas as pd
    from pyproj import CRS, Transformer
    d = pdir(pid)
    npz_yol = d / "cozumleme/grafikler/derinlik_izgara.npz"
    if not npz_yol.exists():
        raise KullaniciHatasi("Bu özellik için temel analizin bu sürümle yeniden çalıştırılması gerekiyor (Yeniden hesapla).")
    tum, zem = d / "cozumleme/morfoloji/tum_golet_grid.csv", d / "cozumleme/zemin/zemin_grid_1m.csv"
    anahtar = (pid, npz_yol.stat().st_mtime, tum.stat().st_mtime if tum.exists() else 0, zem.stat().st_mtime if zem.exists() else 0)
    if anahtar in _izgara_onbellek:
        return _izgara_onbellek[anahtar]
    z = np.load(npz_yol)
    izg = {"epsg": int(z["epsg"]), "Z": {"a": z["Z"].astype(np.float32), "x0": float(z["x0"]), "y1": float(z["y1"]), "h": float(z["hucre"])},
           "T": None, "S": None}
    tr = Transformer.from_crs(4326, CRS.from_epsg(izg["epsg"]), always_xy=True)
    if tum.exists():
        t = pd.read_csv(tum)
        x, y = tr.transform(t["lon"].to_numpy(), t["lat"].to_numpy())
        izg["T"] = _raster_nokta(np.asarray(x), np.asarray(y), t["derinlik"].to_numpy(np.float32))
    if zem.exists():
        g = pd.read_csv(zem)
        g = g[g["sinif"] >= 0]
        if len(g):
            x, y = tr.transform(g["lon"].to_numpy(), g["lat"].to_numpy())
            izg["S"] = _raster_nokta(np.asarray(x), np.asarray(y), g["sinif"].to_numpy(np.float32), kategorik=True)
    _izgara_onbellek.clear()
    _izgara_onbellek[anahtar] = izg
    return izg


def profil_ornekle(pid: str, noktalar: list) -> dict:
    import numpy as np
    from pyproj import CRS, Transformer
    izg = izgara_yukle(pid)
    tr = Transformer.from_crs(4326, CRS.from_epsg(izg["epsg"]), always_xy=True)
    x, y = tr.transform([p[1] for p in noktalar], [p[0] for p in noktalar])
    mes, kx, ky, top = [], [], [], 0.0
    for i in range(len(x) - 1):
        L = math.hypot(x[i + 1] - x[i], y[i + 1] - y[i])
        n = max(2, int(L / 0.5) + 1)
        for j in range(n if i == len(x) - 2 else n - 1):
            f = j / (n - 1)
            kx.append(x[i] + f * (x[i + 1] - x[i]))
            ky.append(y[i] + f * (y[i + 1] - y[i]))
            mes.append(round(top + f * L, 2))
        top += L
    kx, ky = np.array(kx), np.array(ky)
    v1 = _ornek(izg["Z"], kx, ky)
    v2 = _ornek(izg["T"], kx, ky) if izg["T"] else np.full(kx.shape, np.nan, np.float32)
    kay = np.where(np.isfinite(v1), 1, np.where(np.isfinite(v2), 2, 0))
    der = np.where(np.isfinite(v1), v1, v2)
    return {"mesafe": mes, "derinlik": [None if not np.isfinite(v) else round(float(v), 3) for v in der],
            "kaynak": [int(k) for k in kay], "uzunluk": round(top, 1)}


def yuzey3d(pid: str, poligon, tahmin: bool, adim: float) -> dict:
    """Secilen alan (enlem/boylam coklu cizgisi; None = tum olculen alan) icin duzenli derinlik izgarasi."""
    import numpy as np
    from pyproj import CRS, Transformer
    izg = izgara_yukle(pid)
    kaynaklar = [izg["Z"]] + ([izg["T"]] if (tahmin and izg["T"]) else [])
    tr = Transformer.from_crs(4326, CRS.from_epsg(izg["epsg"]), always_xy=True)
    if poligon and len(poligon) >= 3:
        px, py = tr.transform([float(p[1]) for p in poligon], [float(p[0]) for p in poligon])
        px, py = np.asarray(px), np.asarray(py)
        xa, xb, ya, yb = px.min(), px.max(), py.min(), py.max()
    else:
        px = py = None
        xa, xb, ya, yb = 1e18, -1e18, 1e18, -1e18
        for R in kaynaklar:
            r, c = np.nonzero(np.isfinite(R["a"]))
            if r.size:
                xa, xb = min(xa, R["x0"] + c.min() * R["h"]), max(xb, R["x0"] + (c.max() + 1) * R["h"])
                ya, yb = min(ya, R["y1"] - (r.max() + 1) * R["h"]), max(yb, R["y1"] - r.min() * R["h"])
        if xa > xb:
            raise KullaniciHatasi("Bu projede 3B yüzey üretilecek derinlik verisi yok.")
    if xb - xa < 3 or yb - ya < 3:
        raise KullaniciHatasi("Seçilen alan çok küçük; en az birkaç metrelik bir alan seçin.")
    h = float(adim) if adim and adim > 0 else 1.0
    while ((xb - xa) / h) * ((yb - ya) / h) > 220_000:      # tarayici icin ust sinir
        h = round(h + 0.5, 2) if h < 2 else round(h * 1.25, 2)
    nx, ny = int(math.ceil((xb - xa) / h)), int(math.ceil((yb - ya) / h))
    cx = xa + (np.arange(nx) + 0.5) * h
    cy = yb - (np.arange(ny) + 0.5) * h
    GX, GY = np.meshgrid(cx, cy)
    der = np.full(GX.shape, np.nan, np.float32)
    kay = np.zeros(GX.shape, np.int8)
    for k, R in enumerate(kaynaklar, 1):
        v = _ornek(R, GX, GY)
        al = ~np.isfinite(der) & np.isfinite(v)
        der[al], kay[al] = v[al], k
    if px is not None:                                       # cokgen disini maskele (isin dogrultma)
        ic = np.zeros(GX.shape, bool)
        n = len(px)
        for i in range(n):
            x1, y1, x2, y2 = px[i], py[i], px[(i + 1) % n], py[(i + 1) % n]
            if y1 == y2:
                continue
            kes = ((y1 > GY) != (y2 > GY)) & (GX < (x2 - x1) * (GY - y1) / (y2 - y1) + x1)
            ic ^= kes
        der[~ic] = np.nan
        kay[~ic] = 0
    gecerli = np.isfinite(der)
    if not gecerli.any():
        raise KullaniciHatasi("Seçilen alanda derinlik verisi yok. Ölçüm hattının geçtiği bir alan seçin ya da 'tahmini alanı dahil et'i açın.")
    zs = None
    if izg["S"]:
        s_ = _ornek(izg["S"], GX, GY)
        zs = [None if not np.isfinite(v) else int(v) for v in s_.ravel()]
    mx, my = float(np.mean(cx[gecerli.any(0)])), float(np.mean(cy[gecerli.any(1)]))
    lon0, lat0 = Transformer.from_crs(CRS.from_epsg(izg["epsg"]), 4326, always_xy=True).transform(mx, my)
    hu = h * h
    olc, tah = (kay == 1), (kay >= 2)
    ozet = {"alan_m2": round(float(gecerli.sum() * hu)), "olculen_alan_m2": round(float(olc.sum() * hu)),
            "tahmin_alan_m2": round(float(tah.sum() * hu)), "hacim_m3": round(float(np.nansum(der) * hu)),
            "min": round(float(np.nanmin(der)), 3), "max": round(float(np.nanmax(der)), 3), "ort": round(float(np.nanmean(der)), 3),
            "genislik_m": round(float(xb - xa), 1), "yukseklik_m": round(float(yb - ya), 1)}
    return {"nx": nx, "ny": ny, "h": h, "epsg": izg["epsg"], "x0": float(xa), "y1": float(yb), "merkez": [lat0, lon0],
            "z": [None if not np.isfinite(v) else round(float(v), 3) for v in der.ravel()], "k": [int(v) for v in kay.ravel()],
            "s": zs, "ozet": ozet, "tahmin_var": bool(izg["T"])}


# ---------------------------------------------------------------- uygulama
app = FastAPI(title=surum.AD)


@app.exception_handler(KullaniciHatasi)
async def kullanici_hatasi(request, exc):
    from fastapi.responses import JSONResponse
    return JSONResponse({"detail": str(exc)}, status_code=400)


@app.middleware("http")
async def onbellek_yok(request, call_next):
    yanit = await call_next(request)
    if request.url.path == "/" or request.url.path.startswith("/static/app.") or request.url.path.startswith("/static/dil."):
        yanit.headers["Cache-Control"] = "no-cache"
    return yanit


_basladi = False


def baslat_isci():
    global _basladi
    if _basladi:
        return
    _basladi = True
    for p in sorted(PROJELER.iterdir()):
        if not (p / "proje.json").exists():
            continue
        try:
            v = oku(p.name)
        except Exception:
            continue
        # eski surumle hesaplanmis projeler: yeni ciktilar (izgara, hacim tablosu, belirsizlik) icin yeniden hesaplama oner
        if v["analizler"].get("temel", {}).get("durum") == "bitti" and not (p / "cozumleme/grafikler/derinlik_izgara.npz").exists()                 and not v.get("guncel_degil"):
            proje_degistir(p.name, lambda x: x.__setitem__("guncel_degil", True))
        for tur in SIRA:
            if v["analizler"].get(tur, {}).get("durum") in ("bekliyor", "calisiyor"):
                jeton = uuid.uuid4().hex[:8]
                guncelle(p.name, tur, durum="bekliyor", jeton=jeton)
                is_kuyrugu.put((p.name, tur, jeton))
    threading.Thread(target=isci, daemon=True).start()


@app.on_event("startup")
def _baslangic():
    baslat_isci()


@app.get("/")
def anasayfa():
    return FileResponse(STATIK / "index.html")


@app.get("/api/analizler")
def analiz_listesi():
    return {k: {"ad": ANALIZLER[k]["ad"], "gerekir": ANALIZLER[k]["gerekir"], "adimlar": [a[2] for a in ANALIZLER[k]["adimlar"]]} for k in SIRA}


@app.get("/api/hakkinda")
def hakkinda():
    import importlib.metadata as md
    kut = []
    for ad, paket in [("PINGVerter", "pingverter"), ("FastAPI", "fastapi"), ("Uvicorn", "uvicorn"), ("pywebview", "pywebview"),
                      ("NumPy", "numpy"), ("pandas", "pandas"), ("Matplotlib", "matplotlib"), ("Pillow", "pillow"),
                      ("pyproj / PROJ", "pyproj"), ("pyshp", "pyshp")]:
        try:
            m = md.metadata(paket)
            lis = m.get("License-Expression") or ""
            if not lis:
                sinif = [c.split("::")[-1].strip() for c in (m.get_all("Classifier") or []) if c.startswith("License")]
                lis = sinif[0] if sinif else (m.get("License") or "").split("\n")[0][:40]
            kut.append({"ad": ad, "surum": m.get("Version"), "lisans": lis})
        except Exception:
            kut.append({"ad": ad, "surum": "?", "lisans": ""})
    kut += [{"ad": "Leaflet", "surum": "1.9", "lisans": "BSD-2-Clause"}, {"ad": "Chart.js", "surum": "4", "lisans": "MIT"},
            {"ad": "Three.js", "surum": "r128", "lisans": "MIT"},
            {"ad": "Esri World Imagery (uydu altlığı)", "surum": "", "lisans": "Esri kullanım koşulları"},
            {"ad": "CARTO / OpenStreetMap (koyu altlık)", "surum": "", "lisans": "ODbL / CARTO koşulları"}]
    return {"ad": surum.AD, "surum": surum.SURUM, "telif": surum.TELIF, "lisans": surum.LISANS, "web": surum.WEB,
            "python": sys.version.split()[0], "windows": platform.platform(), "paketli": DONDURULMUS, "kutuphaneler": kut,
            "veri_klasoru": str(PROJELER)}


@app.get("/api/ayarlar")
def ayar_oku():
    return {"ayarlar": ayarlar(), "koordinatlar": KOORDINAT_ADLARI, "paletler": PALETLER, "surum": surum.SURUM,
            "logo_var": bool(ayarlar().get("firma_logo")) and Path(ayarlar()["firma_logo"]).exists()}


@app.put("/api/ayarlar")
def ayar_kaydet(veri: dict):
    return {"ayarlar": ayar_yaz(veri)}


def logo_kaydet(veri: bytes) -> str:
    from PIL import Image
    try:
        im = Image.open(io.BytesIO(veri))
        im.load()
    except Exception:
        raise KullaniciHatasi("Logo dosyası bir resim (PNG / JPG) olmalı.")
    im = im.convert("RGBA")
    im.thumbnail((800, 400))
    yol = UYGULAMA_KOK / "firma_logo.png"
    im.save(yol)
    ayar_yaz({"firma_logo": str(yol)})
    return str(yol)


@app.post("/api/ayarlar/logo")
async def logo_yukle(dosya: UploadFile = File(...)):
    return {"yol": logo_kaydet(await dosya.read())}


@app.delete("/api/ayarlar/logo")
def logo_sil():
    ayar_yaz({"firma_logo": ""})
    try:
        (UYGULAMA_KOK / "firma_logo.png").unlink()
    except OSError:
        pass
    return {"tamam": True}


@app.get("/api/ayarlar/logo")
def logo_getir():
    y = ayarlar().get("firma_logo")
    if not y or not Path(y).exists():
        raise HTTPException(404)
    return FileResponse(y, headers={"Cache-Control": "no-store"})


@app.get("/api/guncelleme")
def guncelleme(zorla: int = 0):
    try:
        return guncelleme_denetle(bool(zorla))
    except Exception as e:  # noqa: BLE001
        return {"mevcut": surum.SURUM, "yeni_var": False, "hata": f"Güncelleme sunucusuna ulaşılamadı ({type(e).__name__})"}


@app.post("/api/guncelleme/indir")
def guncelleme_indir_api():
    guncelleme_indir()
    return INDIRME


@app.get("/api/guncelleme/durum")
def guncelleme_durum():
    return INDIRME


@app.post("/api/guncelleme/kur")
def guncelleme_kur_api():
    return guncelleme_kur()


@app.get("/api/hata-raporu")
def hata_raporu_indir(pid: str = ""):
    if pid:
        pdir(pid)
    ad = f"BAHR_hata_raporu_{datetime.now():%Y%m%d_%H%M}.zip"
    return Response(hata_raporu(pid or None), media_type="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="{ad}"'})


@app.get("/api/dogrulama-sablonu")
def dogrulama_sablonu():
    metin = ("nokta;enlem;boylam;derinlik_m;zemin\n"
             "N1;39.890512;32.739021;2,45;çamur\n"
             "N2;39.890640;32.739310;2,10;kum\n"
             "N3;39.890402;32.738870;;çakıl\n")
    return Response(("﻿" + metin).encode("utf-8"), media_type="text/csv",
                    headers={"Content-Disposition": 'attachment; filename="dogrulama_sablonu.csv"'})


def proje_ozetli(p: Path) -> dict:
    v = oku(p.name)
    oz = p / "cozumleme/web/ozet.json"
    if oz.exists():
        try:
            v["ozet"] = json.loads(oz.read_text(encoding="utf-8"))
        except Exception:
            pass
    return v


@app.get("/api/projeler")
def projeler():
    out = []
    for p in PROJELER.iterdir():
        if (p / "proje.json").exists():
            try:
                out.append(proje_ozetli(p))
            except Exception:
                continue
    return sorted(out, key=lambda v: v.get("olusturma", 0), reverse=True)


@app.post("/api/projeler")
async def proje_olustur(dosya: UploadFile = File(...), ad: str = Form("")):
    if not dosya.filename.lower().endswith(".rsd"):
        raise KullaniciHatasi("Yalnızca Garmin .RSD dosyaları destekleniyor")
    pid, d = proje_kaydi_olustur()
    with open(d / "ham.RSD", "wb") as f:
        shutil.copyfileobj(dosya.file, f, length=8 * 1024 * 1024)
    try:
        rsd_dogrula(d / "ham.RSD", dosya.filename)
    except KullaniciHatasi:
        shutil.rmtree(d, ignore_errors=True)
        raise
    return proje_bitir(pid, d, dosya.filename, ad)


@app.get("/api/projeler/{pid}")
def proje(pid: str):
    d = pdir(pid)
    v = proje_ozetli(d)
    v["kuyruk"] = is_kuyrugu.qsize()
    v["etkin_parametreler"] = proje_parametreleri(v)
    v["dogrulama_var"] = (d / "dogrulama.csv").exists()
    return v


@app.patch("/api/projeler/{pid}")
def proje_adi(pid: str, veri: dict):
    pdir(pid)

    def f(v):
        if "ad" in veri and str(veri["ad"]).strip():
            v["ad"] = str(veri["ad"]).strip()[:120]
    return proje_degistir(pid, f)


@app.patch("/api/projeler/{pid}/parametreler")
def proje_parametre(pid: str, veri: dict):
    pdir(pid)
    yeni = ayar_dogrula({k: veri[k] for k in PROJE_PARAMETRELERI if k in veri})
    sonuc_etkiler = {"ses_hizi_modu", "ses_hizi_elle", "cihaz_ses_hizi", "batma_payi", "su_kotu"}

    def f(v):
        eski = dict(v.get("parametreler") or {})
        v.setdefault("parametreler", {}).update(yeni)
        if any(eski.get(k) != v["parametreler"].get(k) for k in sonuc_etkiler & yeni.keys()):
            v["guncel_degil"] = True
    return proje_degistir(pid, f)


@app.post("/api/projeler/{pid}/yeniden")
def proje_yeniden(pid: str):
    pdir(pid)
    return {"siradaki": yeniden_hesapla(pid), "proje": oku(pid)}


@app.delete("/api/projeler/{pid}")
def proje_sil(pid: str):
    d = pdir(pid)
    v = oku(pid)
    if any(a.get("durum") in ("bekliyor", "calisiyor") for a in v["analizler"].values()):
        raise KullaniciHatasi("Çalışan analiz varken proje silinemez")
    shutil.rmtree(d)
    return {"silindi": pid}


@app.post("/api/projeler/{pid}/analiz/{tur}")
def analiz_baslat(pid: str, tur: str):
    pdir(pid)
    if tur not in ANALIZLER:
        raise HTTPException(404, "Bilinmeyen analiz")
    if tur == "dogrulama" and not (PROJELER / pid / "dogrulama.csv").exists():
        raise KullaniciHatasi("Önce doğrulama verisini (CSV) yükleyin.")
    if tur == "degisim" and not proje_parametreleri(oku(pid)).get("degisim_proje"):
        raise KullaniciHatasi("Önce karşılaştırılacak projeyi seçin.")
    kuyruga_ekle(pid, tur)
    return oku(pid)


@app.post("/api/projeler/{pid}/analiz/{tur}/iptal")
def analiz_iptal_api(pid: str, tur: str):
    pdir(pid)
    analiz_iptal(pid, tur)
    return oku(pid)


@app.post("/api/projeler/{pid}/kayitlar")
async def kayit_yukle(pid: str, dosya: UploadFile = File(...)):
    d = pdir(pid)
    if not dosya.filename.lower().endswith(".rsd"):
        raise KullaniciHatasi("Yalnızca Garmin .RSD dosyaları destekleniyor")
    gecici = d / f"_yukleniyor_{uuid.uuid4().hex[:6]}.RSD"
    with open(gecici, "wb") as f:
        shutil.copyfileobj(dosya.file, f, length=8 * 1024 * 1024)
    try:
        return kayit_ekle(pid, gecici, dosya.filename, tasi=True)
    finally:
        if gecici.exists():
            gecici.unlink()


@app.delete("/api/projeler/{pid}/kayitlar/{dosya}")
def kayit_sil(pid: str, dosya: str):
    return kayit_cikar(pid, dosya)


@app.get("/api/projeler/{pid}/duzeltmeler")
def duzeltme_oku(pid: str):
    f = pdir(pid) / "duzeltmeler.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {"dip": [], "silinen": []}


@app.put("/api/projeler/{pid}/duzeltmeler")
def duzeltme_yaz(pid: str, veri: dict):
    d = pdir(pid)
    v = oku(pid)
    if any(a.get("durum") in ("bekliyor", "calisiyor") for a in v["analizler"].values()):
        raise KullaniciHatasi("Çalışan analiz varken düzeltme kaydedilemez.")
    try:
        temiz = {"dip": [{"noktalar": [[int(s), round(float(z), 3)] for s, z in c["noktalar"]]} for c in veri.get("dip", []) if len(c.get("noktalar", [])) >= 2],
                 "silinen": [[int(a), int(b)] for a, b in veri.get("silinen", [])]}
    except Exception:
        raise KullaniciHatasi("Düzeltme verisi okunamadı")
    (d / "duzeltmeler.json").write_text(json.dumps(temiz), encoding="utf-8")
    # kesitte hemen gorunsun diye duzeltilmis meta'yi yeniden uret (birkac saniye)
    if (d / "cozumleme/meta/B001_ds_hifreq_meta_ham.csv").exists():
        parametre_dosyasi_yaz(pid)
        subprocess.run(motor_komutu("duzelt.py", []), cwd=d, env=dict(os.environ, **MOTOR_ORTAM), capture_output=True,
                       timeout=180, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    proje_degistir(pid, lambda v: v.__setitem__("guncel_degil", True))
    return temiz


@app.get("/api/projeler/{pid}/notlar")
def not_oku(pid: str):
    f = pdir(pid) / "notlar.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else []


@app.put("/api/projeler/{pid}/notlar")
def not_yaz(pid: str, veri: list):
    d = pdir(pid)
    temiz = []
    for n in veri[:500]:
        try:
            temiz.append({"id": str(n.get("id") or uuid.uuid4().hex[:8])[:16], "lat": float(n["lat"]), "lon": float(n["lon"]),
                          "baslik": str(n.get("baslik", ""))[:120], "metin": str(n.get("metin", ""))[:1000],
                          "renk": str(n.get("renk", "#f59e0b"))[:9], "tarih": n.get("tarih") or datetime.now().isoformat(timespec="minutes")})
        except Exception:
            continue
    (d / "notlar.json").write_text(json.dumps(temiz, ensure_ascii=False, indent=1), encoding="utf-8")
    return temiz


@app.post("/api/projeler/{pid}/yuzey3d")
def yuzey3d_api(pid: str, veri: dict):
    pdir(pid)
    return yuzey3d(pid, veri.get("poligon"), bool(veri.get("tahmin", True)), float(veri.get("adim") or 0))


@app.post("/api/projeler/{pid}/3b-kaydet")
async def uc_b_kaydet(pid: str, ad: str, request: Request):
    """3B gorunumden uretilen dosyayi (PNG / OBJ / STL) projeye yazar; arayuz sonra Kaydet penceresini acar."""
    d = pdir(pid)
    ad = re.sub(r"[^A-Za-z0-9_.-]+", "_", ad)[:80]
    if not ad.lower().endswith((".png", ".obj", ".stl")):
        raise KullaniciHatasi("Desteklenmeyen dosya türü")
    veri = await request.body()
    if len(veri) > 120_000_000:
        raise KullaniciHatasi("Dosya çok büyük")
    (d / "cozumleme/3b").mkdir(parents=True, exist_ok=True)
    yol = d / "cozumleme/3b" / ad
    if yol.exists():
        yol.unlink()
    yol.write_bytes(veri)
    return {"yol": f"3b/{ad}", "boyut": len(veri)}


@app.get("/api/projeler/{pid}/profil")
def profil(pid: str, yol: str):
    try:
        pts = [[float(a) for a in p.split(",")] for p in yol.split(";") if p.strip()]
    except ValueError:
        raise KullaniciHatasi("Profil hattı okunamadı")
    if len(pts) < 2:
        raise KullaniciHatasi("Profil için en az iki nokta gerekli")
    return profil_ornekle(pid, pts[:200])


async def dogrulama_kaydet(pid: str, veri: bytes):
    d = pdir(pid)
    if len(veri) > 5_000_000:
        raise KullaniciHatasi("Doğrulama dosyası çok büyük")
    (d / "dogrulama.csv").write_bytes(veri)


@app.post("/api/projeler/{pid}/dogrulama")
async def dogrulama_yukle(pid: str, dosya: UploadFile = File(...)):
    await dogrulama_kaydet(pid, await dosya.read())
    kuyruga_ekle(pid, "dogrulama")
    return oku(pid)


@app.post("/api/projeler/{pid}/kalibrasyon")
def kalibrasyon(pid: str, veri: dict):
    d = pdir(pid)
    j = d / "cozumleme/web/dogrulama.json"
    if not j.exists():
        raise KullaniciHatasi("Önce doğrulama analizini çalıştırın.")
    s = json.loads(j.read_text(encoding="utf-8"))
    yapilan = []
    if veri.get("derinlik") and (s.get("derinlik") or {}).get("oneri"):
        proje_parametre(pid, s["derinlik"]["oneri"])
        yapilan.append("derinlik")
    if veri.get("zemin") and (s.get("zemin") or {}).get("oneri"):
        adlar = {k: f'{o["ad"].capitalize()} (numune {o["destek"]})' for k, o in s["zemin"]["oneri"].items()}
        (d / "sinif_adlari.json").write_text(json.dumps(adlar, ensure_ascii=False), encoding="utf-8")
        proje_degistir(pid, lambda v: v.__setitem__("guncel_degil", True))
        yapilan.append("zemin")
    if yapilan:
        yeniden_hesapla(pid)
    return {"uygulanan": yapilan, "proje": oku(pid)}


@app.get("/api/projeler/{pid}/web/{ad}")
def web_dosyasi(pid: str, ad: str):
    k = (pdir(pid) / "cozumleme/web").resolve()
    f = (k / ad).resolve()
    if f.parent != k or not f.exists():
        raise HTTPException(404)
    return FileResponse(f, headers={"Cache-Control": "no-cache"})


GORUNUR = {".png", ".csv", ".gpx", ".html", ".pdf", ".zip", ".tif", ".kml", ".dxf", ".xyz", ".txt", ".obj", ".stl"}


@app.get("/api/projeler/{pid}/dosyalar")
def dosyalar(pid: str):
    k = pdir(pid) / "cozumleme"
    out = []
    if k.exists():
        for f in sorted(k.rglob("*")):
            r = f.relative_to(k)
            if f.is_file() and f.suffix.lower() in GORUNUR and not any(s.startswith("_") for s in r.parts) \
                    and r.parts[0] not in ("web", "meta") and not (r.parts[0] == "disari" and len(r.parts) > 2):
                out.append({"yol": r.as_posix(), "klasor": r.parts[0] if len(r.parts) > 1 else "",
                            "boyut": f.stat().st_size, "tur": f.suffix.lower()[1:]})
    return out


def cikti_yolu(pid: str, yol: str) -> Path:
    k = (pdir(pid) / "cozumleme").resolve()
    f = (k / yol).resolve()
    if k not in f.parents or not f.is_file():
        raise HTTPException(404)
    return f


@app.api_route("/api/projeler/{pid}/dosya/{yol:path}", methods=["GET", "HEAD"])
def dosya(pid: str, yol: str, indir: int = 0):
    f = cikti_yolu(pid, yol)
    return FileResponse(f, filename=f.name if indir else None)


@app.get("/api/projeler/{pid}/kesit")
def kesit(pid: str, merkez: int, genislik: int = 600, palet: str = "bakir", dmax: float = 0):
    d = pdir(pid)
    if not (d / "cozumleme/meta/B001_ds_hifreq_meta.csv").exists():
        raise HTTPException(409, "Önce temel analiz tamamlanmalı")
    genislik = max(100, min(int(genislik), 2400))
    if dmax <= 0:
        oz = d / "cozumleme/web/ozet.json"
        dmax = json.loads(oz.read_text(encoding="utf-8"))["kesit_derinlik_max"] if oz.exists() else 6.0
    png, a0, a1, dip = kesit_png(str(d), merkez, genislik, float(dmax), 360, palet)
    adim = max(1, len(dip) // 600)
    return Response(png, media_type="image/png",
                    headers={"X-Kesit": json.dumps({"a0": a0, "a1": a1, "dmax": dmax, "adim": adim}),
                             "X-Dip": json.dumps(dip[::adim]),
                             "Access-Control-Expose-Headers": "X-Kesit, X-Dip", "Cache-Control": "no-store"})


app.mount("/static", StaticFiles(directory=STATIK), name="static")
