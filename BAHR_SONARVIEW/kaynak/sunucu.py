"""BAHR SONARVIEW - yerel sunucu (arayuz ve analiz kuyrugu).

Hem gelistirme ortaminda (python bahr_sonarview.py) hem de PyInstaller ile
paketlenmis .exe icinde calisir.
"""
import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

DONDURULMUS = getattr(sys, "frozen", False)
# kaynaklar (salt okunur): .exe icinde _MEIPASS, gelistirmede bu klasor
KAYNAK = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
MOTOR = KAYNAK / "motor"
STATIK = KAYNAK / "static"
# veriler (yazilabilir): .exe'nin yaninda, gelistirmede BAHR_SONARVIEW/Projeler
UYGULAMA_KOK = Path(sys.executable).resolve().parent if DONDURULMUS else Path(__file__).resolve().parent.parent
PROJELER = UYGULAMA_KOK / "Projeler"
PROJELER.mkdir(exist_ok=True)
sys.path.insert(0, str(MOTOR))
from kesit import kesit_png  # noqa: E402

ANALIZLER = {
    "temel": {"ad": "Temel analiz", "gerekir": [], "adimlar": [
        ("cozumle.py", [], "Dosya çözülüyor", 2),
        ("analiz.py", [], "Sonar görüntüleri ve grafikler", 3),
        ("kontur.py", [], "Derinlik haritası", 1),
        ("katmanlar.py", ["temel"], "Harita katmanları", 1)]},
    "zemin": {"ad": "Zemin sınıflaması", "gerekir": ["temel"], "adimlar": [
        ("zemin.py", [], "Dip yankıları inceleniyor", 10),
        ("numune.py", [], "Numune noktaları seçiliyor", 1),
        ("katmanlar.py", ["zemin"], "Harita katmanları", 1)]},
    "uydu": {"ad": "Uydu, hacim ve rota", "gerekir": ["temel"], "adimlar": [
        ("uydu.py", [], "Uydu görüntüsü", 2),
        ("morfoloji.py", [], "Hacim, eğim, kapsama, rota", 3),
        ("katmanlar.py", ["uydu"], "Harita katmanları", 1)]},
    "taramalar": {"ad": "Su kolonu ve dip taramaları", "gerekir": ["temel", "zemin"], "adimlar": [
        ("sukolonu_onbellek.py", [], "Su kolonu okunuyor", 5),
        ("sertnokta.py", [], "Kaya / nesne taraması", 1),
        ("bitki.py", [], "Bitki örtüsü taraması", 3),
        ("balik.py", [], "Balık ve kabarcık taraması", 3),
        ("katmanlar.py", ["taramalar"], "Harita katmanları", 1)]},
    "rapor": {"ad": "Rapor", "gerekir": ["temel"], "adimlar": [
        ("rapor.py", [], "Rapor hazırlanıyor", 1)]},
}

kilit = threading.Lock()
is_kuyrugu: "queue.Queue[tuple[str, str]]" = queue.Queue()
calisan_surecler: set = set()


# ---------------------------------------------------------------- proje kaydi
def pdir(pid: str) -> Path:
    p = (PROJELER / pid).resolve()
    if p.parent != PROJELER.resolve() or not (p / "proje.json").exists():
        raise HTTPException(404, "Proje bulunamadı")
    return p


def oku(pid: str) -> dict:
    with open(PROJELER / pid / "proje.json", encoding="utf-8") as f:
        return json.load(f)


def yaz(pid: str, veri: dict):
    tmp = PROJELER / pid / "proje.json.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=1)
    os.replace(tmp, PROJELER / pid / "proje.json")


def guncelle(pid: str, tur: str, **alanlar):
    with kilit:
        v = oku(pid)
        v["analizler"].setdefault(tur, {}).update(alanlar)
        yaz(pid, v)


def motor_komutu(betik: str, args: list) -> list:
    if DONDURULMUS:                                   # .exe kendini motor kipinde cagirir
        return [sys.executable, "--motor", betik, *args]
    return [sys.executable, "-u", str(MOTOR / betik), *args]


# ---------------------------------------------------------------- is calistirici
def calistir(pid: str, tur: str):
    adimlar = ANALIZLER[tur]["adimlar"]
    toplam = sum(a[3] for a in adimlar)
    yapilan = 0
    t0 = time.time()
    guncelle(pid, tur, durum="calisiyor", ilerleme=0.0, adim=adimlar[0][2], mesaj=None, baslangic=t0)
    env = dict(os.environ, PYTHONPATH=str(MOTOR), PYTHONIOENCODING="utf-8", MPLBACKEND="Agg",
               PYTHONWARNINGS="ignore", PYTHONUNBUFFERED="1")
    for betik, args, etiket, agirlik in adimlar:
        guncelle(pid, tur, adim=etiket)
        p = subprocess.Popen(motor_komutu(betik, args), cwd=PROJELER / pid, stdin=subprocess.DEVNULL,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                             errors="replace", env=env, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        calisan_surecler.add(p)
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
                    son = (son + [satir])[-40:]
            p.wait()
        finally:
            calisan_surecler.discard(p)
        with open(PROJELER / pid / "analiz_gunlugu.txt", "a", encoding="utf-8") as g:
            g.write(f"\n=== {datetime.now():%Y-%m-%d %H:%M:%S} {tur} / {betik} (cikis {p.returncode})\n" + "\n".join(son) + "\n")
        if p.returncode != 0:
            hata = next((s for s in reversed(son) if s.startswith("HATA")), None) or (son[-1] if son else "Bilinmeyen hata")
            guncelle(pid, tur, durum="hata", mesaj=f"{etiket}: {hata[:400]}", bitis=time.time())
            return
        yapilan += agirlik
        guncelle(pid, tur, ilerleme=round(yapilan / toplam, 3))
    guncelle(pid, tur, durum="bitti", ilerleme=1.0, adim=None, bitis=time.time(), sure_s=round(time.time() - t0))


def isci():
    while True:
        pid, tur = is_kuyrugu.get()
        try:
            if (PROJELER / pid / "proje.json").exists():
                calistir(pid, tur)
        except Exception as e:  # noqa: BLE001
            try:
                guncelle(pid, tur, durum="hata", mesaj=f"Beklenmeyen hata: {e}")
            except Exception:
                pass
        finally:
            is_kuyrugu.task_done()


def kuyruga_ekle(pid: str, tur: str):
    v = oku(pid)
    for g in ANALIZLER[tur]["gerekir"]:
        if v["analizler"].get(g, {}).get("durum") not in ("bitti", "bekliyor", "calisiyor"):
            raise HTTPException(409, f"Önce '{ANALIZLER[g]['ad']}' çalıştırılmalı")
    if v["analizler"].get(tur, {}).get("durum") in ("bekliyor", "calisiyor"):
        return
    guncelle(pid, tur, durum="bekliyor", ilerleme=0.0, mesaj=None, adim=None)
    is_kuyrugu.put((pid, tur))


def proje_kaydi_olustur(kaynak_ad: str, ad: str) -> tuple[str, Path]:
    pid = datetime.now().strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:4]
    d = PROJELER / pid
    d.mkdir()
    return pid, d


def proje_bitir(pid: str, d: Path, dosya_adi: str, ad: str) -> dict:
    v = {"id": pid, "ad": ad.strip() or Path(dosya_adi).stem, "dosya_adi": dosya_adi,
         "boyut": (d / "ham.RSD").stat().st_size, "olusturma": time.time(), "analizler": {}}
    yaz(pid, v)
    kuyruga_ekle(pid, "temel")
    return oku(pid)


def proje_yoldan(yol: str) -> dict:
    """Masaustu: bilgisayardaki .RSD dosyasini (HTTP yuklemesi olmadan) projeye kopyalar."""
    kaynak = Path(yol)
    if kaynak.suffix.lower() != ".rsd" or not kaynak.is_file():
        raise ValueError("Yalnızca Garmin .RSD dosyaları destekleniyor")
    pid, d = proje_kaydi_olustur(kaynak.name, kaynak.stem)
    shutil.copyfile(kaynak, d / "ham.RSD")
    return proje_bitir(pid, d, kaynak.name, kaynak.stem)


def kapat():
    for p in list(calisan_surecler):
        try:
            p.terminate()
        except Exception:
            pass


# ---------------------------------------------------------------- uygulama
app = FastAPI(title="BAHR SONARVIEW")


@app.middleware("http")
async def onbellek_yok(request, call_next):
    yanit = await call_next(request)
    if request.url.path == "/" or request.url.path.startswith("/static/app."):
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
        v = oku(p.name)
        for tur in ANALIZLER:
            if v["analizler"].get(tur, {}).get("durum") in ("bekliyor", "calisiyor"):
                guncelle(p.name, tur, durum="bekliyor")
                is_kuyrugu.put((p.name, tur))
    threading.Thread(target=isci, daemon=True).start()


@app.get("/")
def anasayfa():
    return FileResponse(STATIK / "index.html")


@app.get("/api/analizler")
def analiz_listesi():
    return {k: {"ad": v["ad"], "gerekir": v["gerekir"], "adimlar": [a[2] for a in v["adimlar"]]} for k, v in ANALIZLER.items()}


@app.get("/api/projeler")
def projeler():
    out = []
    for p in PROJELER.iterdir():
        if (p / "proje.json").exists():
            v = oku(p.name)
            oz = p / "cozumleme/web/ozet.json"
            if oz.exists():
                v["ozet"] = json.loads(oz.read_text(encoding="utf-8"))
            out.append(v)
    return sorted(out, key=lambda v: v["olusturma"], reverse=True)


@app.post("/api/projeler")
async def proje_olustur(dosya: UploadFile = File(...), ad: str = Form("")):
    if not dosya.filename.lower().endswith(".rsd"):
        raise HTTPException(400, "Yalnızca Garmin .RSD dosyaları destekleniyor")
    pid, d = proje_kaydi_olustur(dosya.filename, ad)
    with open(d / "ham.RSD", "wb") as f:
        shutil.copyfileobj(dosya.file, f, length=8 * 1024 * 1024)
    return proje_bitir(pid, d, dosya.filename, ad)


@app.get("/api/projeler/{pid}")
def proje(pid: str):
    d = pdir(pid)
    v = oku(pid)
    oz = d / "cozumleme/web/ozet.json"
    if oz.exists():
        v["ozet"] = json.loads(oz.read_text(encoding="utf-8"))
    v["kuyruk"] = is_kuyrugu.qsize()
    return v


@app.patch("/api/projeler/{pid}")
def proje_adi(pid: str, veri: dict):
    pdir(pid)
    with kilit:
        v = oku(pid)
        if "ad" in veri and str(veri["ad"]).strip():
            v["ad"] = str(veri["ad"]).strip()[:120]
        yaz(pid, v)
    return v


@app.delete("/api/projeler/{pid}")
def proje_sil(pid: str):
    d = pdir(pid)
    v = oku(pid)
    if any(a.get("durum") in ("bekliyor", "calisiyor") for a in v["analizler"].values()):
        raise HTTPException(409, "Çalışan analiz varken proje silinemez")
    shutil.rmtree(d)
    return {"silindi": pid}


@app.post("/api/projeler/{pid}/analiz/{tur}")
def analiz_baslat(pid: str, tur: str):
    pdir(pid)
    if tur not in ANALIZLER:
        raise HTTPException(404, "Bilinmeyen analiz")
    kuyruga_ekle(pid, tur)
    return oku(pid)


@app.get("/api/projeler/{pid}/web/{ad}")
def web_dosyasi(pid: str, ad: str):
    k = (pdir(pid) / "cozumleme/web").resolve()
    f = (k / ad).resolve()
    if f.parent != k or not f.exists():
        raise HTTPException(404)
    return FileResponse(f, headers={"Cache-Control": "no-cache"})


GORUNUR = {".png", ".csv", ".gpx", ".html"}


@app.get("/api/projeler/{pid}/dosyalar")
def dosyalar(pid: str):
    k = pdir(pid) / "cozumleme"
    out = []
    if k.exists():
        for f in sorted(k.rglob("*")):
            r = f.relative_to(k)
            if f.is_file() and f.suffix.lower() in GORUNUR and not any(s.startswith("_") for s in r.parts) \
                    and r.parts[0] not in ("web", "meta"):
                out.append({"yol": r.as_posix(), "klasor": r.parts[0] if len(r.parts) > 1 else "",
                            "boyut": f.stat().st_size, "tur": f.suffix.lower()[1:]})
    return out


def cikti_yolu(pid: str, yol: str) -> Path:
    k = (pdir(pid) / "cozumleme").resolve()
    f = (k / yol).resolve()
    if k not in f.parents or not f.is_file():
        raise HTTPException(404)
    return f


@app.get("/api/projeler/{pid}/dosya/{yol:path}")
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
    return Response(png, media_type="image/png",
                    headers={"X-Kesit": json.dumps({"a0": a0, "a1": a1, "dmax": dmax}),
                             "X-Dip": json.dumps(dip[:: max(1, len(dip) // 300)]),
                             "Access-Control-Expose-Headers": "X-Kesit, X-Dip", "Cache-Control": "no-store"})


app.mount("/static", StaticFiles(directory=STATIK), name="static")
