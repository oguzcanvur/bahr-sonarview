"""BAHR SONARVIEW marka dosyalarini marka/ klasorundeki kaynak gorsellerden uretir.

  marka/kaynak_simge.png  -> simge.ico, simge.png        (pencere / gorev cubugu / exe)
  marka/kaynak_logo.png   -> static/logo.png             (arayuz kosesi, saydam)
                             static/logo_yatay.png       (yazili logo, saydam; rapor ve README)
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

BURASI = Path(__file__).parent
MARKA = BURASI / "marka"


def simge():
    im = Image.open(MARKA / "kaynak_simge.png").convert("RGB")
    a = np.asarray(im).astype(int)
    lacivert = (a[..., 2] - a[..., 0]) > 15          # kare mavi tonlu, arka plan gri
    ys, xs = np.where(lacivert)
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    pay = 14                                          # gri kenar cizgisini kirp
    kutu = (x0 + pay, y0 + pay, x1 - pay, y1 - pay)
    kare = im.crop(kutu).resize((1024, 1024), Image.LANCZOS).convert("RGBA")
    # yuvarlak koseli saydam maske (4x orneklemeyle yumusak kenar)
    S = 4096
    maske = Image.new("L", (S, S), 0)
    ImageDraw.Draw(maske).rounded_rectangle([0, 0, S - 1, S - 1], radius=int(S * 0.2), fill=255)
    kare.putalpha(maske.resize((1024, 1024), Image.LANCZOS))
    kare.save(BURASI / "simge.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    kare.resize((256, 256), Image.LANCZOS).save(BURASI / "simge.png")
    kare.resize((512, 512), Image.LANCZOS).save(MARKA / "simge_512.png")


def saydam(im, zemin):
    """Koyu duz zemin uzerindeki gorseli saydam yapar (zemin rengini ayristirir)."""
    p = np.asarray(im.convert("RGB")).astype(float)
    b = np.array(zemin, float)
    alfa = np.clip(((p - b) / (255 - b)).max(-1), 0, 1)
    alfa = np.clip((alfa - 0.03) / 0.97, 0, 1)        # zemindeki hafif gurultuyu sil
    renk = b + (p - b) / np.maximum(alfa, 1e-3)[..., None]
    out = np.dstack([np.clip(renk, 0, 255), alfa * 255]).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def logo():
    im = Image.open(MARKA / "kaynak_logo.png").convert("RGB")
    a = np.asarray(im).astype(int)
    zemin = np.median(a[:40, :40].reshape(-1, 3), axis=0)
    dolu = a.max(-1) > 40
    ys, xs = np.where(dolu)
    yatay = im.crop((xs.min() - 30, ys.min() - 30, xs.max() + 30, ys.max() + 30))
    yatay = saydam(yatay, zemin)
    yatay.thumbnail((1400, 400), Image.LANCZOS)
    yatay.save(BURASI / "static" / "logo_yatay.png", optimize=True)
    # yalnizca sembol (yazidan onceki kisim)
    ys, xs = np.where(dolu[:, :900])
    sembol = im.crop((xs.min() - 20, ys.min() - 20, xs.max() + 20, ys.max() + 20))
    sembol = saydam(sembol, zemin)
    w, h = sembol.size
    kenar = max(w, h)
    kare = Image.new("RGBA", (kenar, kenar), (0, 0, 0, 0))
    kare.paste(sembol, ((kenar - w) // 2, (kenar - h) // 2))
    kare.resize((160, 160), Image.LANCZOS).save(BURASI / "static" / "logo.png", optimize=True)


if __name__ == "__main__":
    simge()
    logo()
    print("-> simge.ico, simge.png, static/logo.png, static/logo_yatay.png")
