# SonarLab

Garmin balık bulucu sonar kayıtları (`.RSD`) için yerel analiz uygulaması. Bilgisayarında çalışır, tarayıcıda açılır; veriler bu bilgisayardan çıkmaz (yalnızca uydu altlığı internetten alınır).

## Başlatma

Proje klasöründeki **`SonarLab.bat`** dosyasına çift tıkla. Tarayıcıda `http://127.0.0.1:8765` açılır. Kapatmak için açılan siyah pencereyi kapat.

İlk kurulum (başka bir bilgisayarda):

```
py -m venv .venv
.venv\Scripts\python -m pip install -r sonarlab\requirements.txt
```

## Kullanım

1. Garmin cihazın hafıza kartındaki `Sonar*.RSD` dosyasını pencereye sürükle ya da **Yeni kayıt yükle**'ye tıkla.
2. **Temel analiz** kendiliğinden çalışır (~1 dk): rota, derinlik haritası, eş derinlik çizgileri, sonar görüntüleri, grafikler.
3. Sekmeler:
   - **Harita** – uydu üzerinde katmanlar; rotaya tıkla, o noktanın sonar kesiti açılır.
   - **Sonar** – kaydın tamamında gezinilebilen kesit görüntüleyici (çubuk, ←/→ tuşları, boşluk = oynat).
   - **Grafikler** – derinlik, hız, sıcaklık; grafiğe tıkla, o anın kesitine git.
   - **Analizler** – isteğe bağlı analizleri çalıştır.
   - **Dosyalar** – tüm görseller, CSV ve GPX dosyaları, rapor.

## İsteğe bağlı analizler

| Analiz | Süre | Ne üretir | Gerekir |
|---|---|---|---|
| Zemin sınıflaması | ~8 dk | Göreli zemin sınıfları, sertlik / penetrasyon haritaları, numune noktaları (GPX) | Temel |
| Uydu, hacim ve rota | ~1 dk | Kıyı çizgisi, toplam hacim, dip eğimi, kapsama, yeni tarama rotası (GPX) | Temel, internet |
| Su kolonu ve dip taramaları | ~6 dk | Balık ve gaz kabarcığı izleri, kaya / nesne ve bitki örtüsü taraması | Temel, Zemin |
| Rapor | ~10 sn | Çalışmış analizlerin tek dosyalık HTML raporu (tarayıcıdan PDF alınabilir) | Temel |

## Dosyalar nerede

Her yükleme `sonarlab/projeler/<tarih-kimlik>/` altında saklanır: `ham.RSD` (yüklenen dosya), `proje.json`, `cozumleme/` (tüm çıktılar), `cozumleme_gunluk.txt` (analiz günlüğü).

## Sınırlar

- Yalnızca Garmin `.RSD`; kayıttaki aşağı bakan (DownVü) kanal kullanılır.
- Zemin, balık ve bitki sonuçları kalibre edilmemiş bir balık bulucudan elde edilen **göreli** sonuçlardır; kesin zemin tipi için dip numunesi gerekir.
- Vericinin çınlaması nedeniyle yüzeyin ilk ~1,4 m'si su kolonu taramalarında görülmez.
- Uydu altlığı ve kıyı çizgisi için internet gerekir; yoksa analiz düz altlıkla devam eder, hacim hesaplanamaz.
