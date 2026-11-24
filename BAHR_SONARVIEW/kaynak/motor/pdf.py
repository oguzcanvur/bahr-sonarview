"""cozumleme/rapor.html -> cozumleme/rapor.pdf (Microsoft Edge'in basliksiz yazdirma kipiyle).

Edge Windows 10/11'de yerlesik geldigi icin ek kurulum gerekmez. Bulunamazsa adim hata vermez;
HTML rapor yine kullanilabilir (tarayicidan Yazdir -> PDF).
"""
import os
import shutil
import subprocess
import sys
import tempfile
import time

HTML = os.path.abspath("cozumleme/rapor.html")
PDF = os.path.abspath("cozumleme/rapor.pdf")
if not os.path.exists(HTML):
    sys.exit("HATA: Önce HTML rapor oluşturulmalı")

adaylar = [os.path.join(os.environ.get(k, ""), "Microsoft", "Edge", "Application", "msedge.exe")
           for k in ("ProgramFiles(x86)", "ProgramFiles", "LOCALAPPDATA")]
edge = next((a for a in adaylar if os.path.exists(a)), None) or shutil.which("msedge")
if not edge:
    print("UYARI: Microsoft Edge bulunamadı; PDF üretilemedi (HTML rapor hazır).")
    print("@@ilerleme 1.0")
    sys.exit(0)

if os.path.exists(PDF):
    os.remove(PDF)
profil = tempfile.mkdtemp(prefix="bahr_pdf_")
try:
    url = "file:///" + HTML.replace("\\", "/")
    p = subprocess.run([edge, "--headless=new", "--disable-gpu", "--no-first-run", "--disable-extensions",
                        f"--user-data-dir={profil}", "--no-pdf-header-footer", "--run-all-compositor-stages-before-draw",
                        "--virtual-time-budget=15000", f"--print-to-pdf={PDF}", url],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    for _ in range(40):
        if os.path.exists(PDF) and os.path.getsize(PDF) > 0:
            break
        time.sleep(0.25)
finally:
    shutil.rmtree(profil, ignore_errors=True)
if not os.path.exists(PDF):
    sys.exit("HATA: PDF oluşturulamadı (Edge yazdırma başarısız). HTML rapor kullanılabilir.")
print(f"PDF: {os.path.getsize(PDF) / 1e6:.1f} MB")
print("@@ilerleme 1.0")
