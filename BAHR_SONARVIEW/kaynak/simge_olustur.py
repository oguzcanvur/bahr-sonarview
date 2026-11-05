"""BAHR SONARVIEW simgesini (simge.ico) cizer: koyu zemin uzerinde sonar taramasi."""
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

N = 512
img = Image.new("RGBA", (N, N), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
d.rounded_rectangle([16, 16, N - 16, N - 16], radius=110, fill=(9, 16, 30, 255))
c = N / 2
# tarama dilimi (gradyan)
dilim = Image.new("RGBA", (N, N), (0, 0, 0, 0))
dd = ImageDraw.Draw(dilim)
for i in range(70):
    a = 0.85 * (1 - i / 70)
    dd.pieslice([c - 190, c - 190, c + 190, c + 190], -90 - i, -89 - i, fill=(34, 211, 238, int(255 * a * 0.75)))
img.alpha_composite(dilim)
d = ImageDraw.Draw(img)
for r, w, al in [(190, 10, 255), (128, 6, 150), (66, 6, 110)]:
    d.ellipse([c - r, c - r, c + r, c + r], outline=(34, 211, 238, al), width=w)
d.line([c, c, c, c - 190], fill=(165, 243, 252, 255), width=8)
# dip yankisi (alt yay) ve hedef
d.arc([c - 150, c - 40, c + 150, c + 220], 200, 340, fill=(251, 191, 36, 255), width=12)
ang = math.radians(-125)
x, y = c + 105 * math.cos(ang), c + 105 * math.sin(ang)
parlama = Image.new("RGBA", (N, N), (0, 0, 0, 0))
ImageDraw.Draw(parlama).ellipse([x - 26, y - 26, x + 26, y + 26], fill=(255, 255, 255, 160))
img.alpha_composite(parlama.filter(ImageFilter.GaussianBlur(10)))
d.ellipse([x - 13, y - 13, x + 13, y + 13], fill=(255, 255, 255, 255))
d.ellipse([c - 14, c - 14, c + 14, c + 14], fill=(34, 211, 238, 255))

hedef = Path(__file__).with_name("simge.ico")
img.save(hedef, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
img.resize((256, 256), Image.LANCZOS).save(hedef.with_suffix(".png"))
print("->", hedef)
