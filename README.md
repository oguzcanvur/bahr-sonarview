# BAHR SONARVIEW

Garmin balık bulucu sonar kayıtları (`.RSD`) için masaüstü analiz programı. Bir sonar kaydını yükle; derinlik haritası, canlı sonar kesiti, zemin sınıflaması, gölet hacmi, yeni tarama rotası, balık / nesne taramaları ve tek dosyalık rapor üretir.

## İndir ve çalıştır (Windows 10/11)

1. [Releases](../../releases) sayfasından `BAHR_SONARVIEW-windows.zip` dosyasını indir.
2. Zip'i bir klasöre çıkar.
3. `BAHR SONARVIEW\BAHR SONARVIEW.exe` dosyasına çift tıkla.

Python ya da başka bir kurulum gerekmez. Program kendi penceresinde açılır; veriler bilgisayarda kalır (yalnızca uydu altlığı için internet kullanılır). Ayrıntılı kullanım: [BAHR_SONARVIEW/OKU_BENI.md](BAHR_SONARVIEW/OKU_BENI.md).

## Neler yapar

| Analiz | Çıktı |
|---|---|
| Temel (otomatik) | Rota, derinlik haritası, eş derinlik çizgileri, sonar görüntüleri, derinlik / hız / sıcaklık grafikleri |
| Zemin sınıflaması | Dip yankısının genlik şeklinden (sertlik, penetrasyon, sönümlenme) göreli zemin sınıfları, dip numunesi noktaları (GPX) |
| Uydu, hacim ve rota | Uydudan kıyı çizgisi, toplam hacim, dip eğimi, kapsama, eksik alanlar için tarama rotası (GPX) |
| Su kolonu ve dip taramaları | Balık ve gaz kabarcığı izleri, kaya / batık nesne, su bitkisi örtüsü |
| Rapor | Çalışmış analizlerin görselli, tek dosyalık HTML raporu |

Arayüzde: uydu haritası ve katmanlar, haritada tıklanan noktanın sonar kesiti, kayıt boyunca gezinilebilen sonar görüntüleyici, etkileşimli grafikler.

**Sınırlar:** Yalnızca Garmin `.RSD` (aşağı bakan DownVü kanalı). Zemin, balık ve bitki sonuçları kalibre edilmemiş bir balık bulucudan elde edilen **göreli** sonuçlardır; kesin zemin tipi için dip numunesi gerekir.

## Depo yapısı

```
BAHR_SONARVIEW/        Masaüstü programı
  kaynak/              bahr_sonarview.py (pencere), sunucu.py, motor/ (analiz), static/ (arayüz)
  derle.bat            .exe derlemesi (PyInstaller)
  run.bat              derlenmiş programı başlatır
sonarlab/              Aynı uygulamanın tarayıcıda çalışan sürümü (FastAPI)
*.py (kök)             İlk keşif ve analiz betikleri (tek kayıt üzerinde)
```

## Kaynaktan çalıştırma / derleme

```
py -m venv .venv
.venv\Scripts\python -m pip install -r BAHR_SONARVIEW\kaynak\gereksinimler.txt
.venv\Scripts\python BAHR_SONARVIEW\kaynak\bahr_sonarview.py      # geliştirme kipinde aç
BAHR_SONARVIEW\derle.bat                                          # .exe derle
```

RSD dosyaları [PINGVerter](https://github.com/CameronBodine/PINGVerter) ile çözülür. Harita: [Leaflet](https://leafletjs.com), grafikler: [Chart.js](https://www.chartjs.org), uydu altlığı: Esri World Imagery.
