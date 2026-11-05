"""BAHR SONARVIEW - Garmin sonar kayitlari icin masaustu analiz programi.

Calistirma (gelistirme):  python kaynak/bahr_sonarview.py
Paketlenmis hali:         BAHR SONARVIEW.exe

Ayni .exe iki kipte calisir:
  * normal      : kendi penceresinde arayuz + arka planda yerel sunucu
  * --motor ... : analiz motorunun bir adimini calistirir (arayuz bunu kendisi cagirir)
"""
import os
import sys


# ---------------------------------------------------------------- motor kipi
def motor_kipi():
    import runpy
    from pathlib import Path
    kok = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)) / "motor"
    betik, args = sys.argv[2], sys.argv[3:]
    # pencereli .exe'de stdout yok olabilir: ust surecin borusuna dogrudan baglan
    try:
        if sys.stdout is None:
            sys.stdout = open(1, "w", encoding="utf-8", buffering=1, closefd=False)
        else:
            sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    except Exception:
        sys.stdout = open(os.devnull, "w")
    if sys.stderr is None:
        sys.stderr = sys.stdout
    os.environ.setdefault("MPLBACKEND", "Agg")
    import warnings
    warnings.filterwarnings("ignore")
    sys.path.insert(0, str(kok))
    sys.argv = [str(kok / betik), *args]
    kod = 0
    try:
        runpy.run_path(str(kok / betik), run_name="__main__")
    except SystemExit as e:
        if isinstance(e.code, str):
            print(e.code)
            kod = 1
        else:
            kod = e.code or 0
    except Exception as e:  # noqa: BLE001
        import traceback
        traceback.print_exc(file=sys.stdout)
        print(f"HATA: {type(e).__name__}: {e}")
        kod = 1
    sys.stdout.flush()
    os._exit(kod)


if len(sys.argv) > 2 and sys.argv[1] == "--motor":
    motor_kipi()

# ---------------------------------------------------------------- arayuz kipi
# Pencereli .exe'de konsol yok: cikti ve hatalar program_gunlugu.txt'ye
if sys.stdout is None or sys.stderr is None:
    from pathlib import Path as _P
    _kok = _P(sys.executable).resolve().parent if getattr(sys, "frozen", False) else _P(__file__).resolve().parent.parent
    _g = open(_kok / "program_gunlugu.txt", "w", encoding="utf-8", buffering=1)
    sys.stdout = sys.stdout or _g
    sys.stderr = sys.stderr or _g
if os.environ.get("BAHR_TANILAMA"):
    import faulthandler
    faulthandler.dump_traceback_later(int(os.environ["BAHR_TANILAMA"]), repeat=False, file=sys.stderr)

import ctypes  # noqa: E402
import shutil  # noqa: E402
import socket  # noqa: E402
import threading  # noqa: E402
import time  # noqa: E402
import webbrowser  # noqa: E402

import _bagimliliklar  # noqa: E402,F401  (paketleyicinin motor kutuphanelerini tanimasi icin)
import sunucu  # noqa: E402

AD = "BAHR SONARVIEW"


def mesaj(metin, baslik=AD):
    try:
        ctypes.windll.user32.MessageBoxW(None, metin, baslik, 0x40)
    except Exception:
        print(metin)


def tek_kopya():
    """Program zaten aciksa ikinci kopyayi acma (Projeler klasorundeki kilit dosyasi)."""
    import msvcrt
    f = open(sunucu.PROJELER / ".kilit", "a+")
    try:
        msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        return None
    return f


def bos_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


class Api:
    """Arayuzden (JavaScript) cagrilan yerel islemler."""

    def __init__(self):
        self._pencere = None

    def kayit_ac(self):
        import webview
        r = self._pencere.create_file_dialog(webview.FileDialog.OPEN, allow_multiple=False,
                                            file_types=("Garmin sonar kaydı (*.RSD;*.rsd)", "Tüm dosyalar (*.*)"))
        if not r:
            return None
        try:
            return sunucu.proje_yoldan(r[0] if isinstance(r, (list, tuple)) else r)
        except Exception as e:  # noqa: BLE001
            return {"hata": str(e)}

    def dosya_kaydet(self, pid, yol):
        import webview
        try:
            kaynak = sunucu.cikti_yolu(pid, yol)
        except Exception:
            return {"hata": "Dosya bulunamadı"}
        r = self._pencere.create_file_dialog(webview.FileDialog.SAVE, save_filename=kaynak.name)
        if not r:
            return None
        hedef = r[0] if isinstance(r, (list, tuple)) else r
        shutil.copyfile(kaynak, hedef)
        return {"kaydedildi": str(hedef)}

    def klasor_ac(self, pid=None):
        yol = sunucu.PROJELER if not pid else sunucu.PROJELER / pid / "cozumleme"
        os.startfile(str(yol if yol.exists() else sunucu.PROJELER))
        return True

    def rapor_ac(self, pid):
        try:
            os.startfile(str(sunucu.cikti_yolu(pid, "rapor.html")))
            return True
        except Exception:
            return {"hata": "Rapor bulunamadı"}

    def disari_ac(self, url):
        if str(url).startswith(("http://", "https://")):
            webbrowser.open(url)
        return True


def main():
    kilit = tek_kopya()
    if kilit is None:
        mesaj(f"{AD} zaten açık. Görev çubuğundaki pencereyi kullanın.")
        return

    import uvicorn
    import webview

    port = bos_port()
    cfg = uvicorn.Config(sunucu.app, host="127.0.0.1", port=port, log_level="warning",
                         log_config=None, access_log=False)
    srv = uvicorn.Server(cfg)
    threading.Thread(target=srv.run, daemon=True).start()
    for _ in range(200):
        if srv.started:
            break
        time.sleep(0.05)
    sunucu.baslat_isci()
    (sunucu.UYGULAMA_KOK / ".port").write_text(str(port))      # tanilama icin

    api = Api()
    webview.settings["ALLOW_DOWNLOADS"] = True
    webview.settings["OPEN_EXTERNAL_LINKS_IN_BROWSER"] = True
    pencere = webview.create_window(AD, f"http://127.0.0.1:{port}/", js_api=api, width=1440, height=900,
                                    min_size=(1000, 640), background_color="#070b14", text_select=True)
    api._pencere = pencere

    def kapandi():
        sunucu.kapat()
        srv.should_exit = True

    pencere.events.closed += kapandi
    veri = sunucu.UYGULAMA_KOK / ".pencere"
    webview.start(gui="edgechromium", private_mode=False, storage_path=str(veri))
    sunucu.kapat()
    os._exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001
        import traceback
        (sunucu.UYGULAMA_KOK / "hata_gunlugu.txt").write_text(traceback.format_exc(), encoding="utf-8")
        mesaj(f"{AD} başlatılamadı:\n{e}\n\nAyrıntı: hata_gunlugu.txt")
