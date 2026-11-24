"""PyInstaller icin Windows surum bilgisi dosyasi uretir (Dosya > Ozellikler > Ayrintilar)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import surum  # noqa: E402

p = [int(x) for x in surum.SURUM.split(".")] + [0]
hedef = Path(sys.argv[1] if len(sys.argv) > 1 else "surum_bilgisi.txt")
hedef.parent.mkdir(parents=True, exist_ok=True)
hedef.write_text(f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers=({p[0]}, {p[1]}, {p[2]}, 0), prodvers=({p[0]}, {p[1]}, {p[2]}, 0),
    mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('041F04B0', [
      StringStruct('CompanyName', 'BAHR'),
      StringStruct('FileDescription', '{surum.AD} - Garmin sonar analiz programı'),
      StringStruct('FileVersion', '{surum.SURUM}'),
      StringStruct('InternalName', 'BAHR SONARVIEW'),
      StringStruct('LegalCopyright', '{surum.TELIF}'),
      StringStruct('OriginalFilename', 'BAHR SONARVIEW.exe'),
      StringStruct('ProductName', '{surum.AD}'),
      StringStruct('ProductVersion', '{surum.SURUM}')])]),
    VarFileInfo([VarStruct('Translation', [0x041F, 1200])])
  ]
)
""", encoding="utf-8")
print("->", hedef)
