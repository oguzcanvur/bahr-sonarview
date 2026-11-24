# BAHR SONARVIEW

Garmin balık bulucu sonar kayıtları (`.RSD`) için masaüstü analiz programı. Kendi penceresinde çalışır; tarayıcı ya da Python kurulumu gerektirmez. İnternet yalnızca uydu altlığı ve güncelleme denetimi için kullanılır.

## Açmak

Bu klasördeki **`run.bat`** ya da **`BAHR SONARVIEW`** kısayoluna çift tıkla (ikisi de `BAHR SONARVIEW\BAHR SONARVIEW.exe`'yi açar).

- Masaüstüne kısayol için: `.exe`'ye sağ tıkla → *Daha fazla seçenek göster* → *Gönder* → *Masaüstü (kısayol oluştur)*.
- Program zaten açıksa ikinci kez açılmaz; açık pencereyi kullan.
- `BAHR SONARVIEW` klasörü taşınabilir: klasörün tamamını başka bir yere ya da başka bir Windows bilgisayara kopyalayabilirsin (içindeki `_internal` klasörüyle birlikte).

## Kullanım

1. **Yeni kayıt yükle**'ye tıkla ve Garmin cihazın hafıza kartındaki `Sonar*.RSD` dosyasını seç (ya da dosyayı pencereye sürükle). Bozuk ya da Garmin olmayan dosyalar yüklenmeden reddedilir.
2. **Temel analiz** kendiliğinden çalışır (~1 dk). Aynı göletin başka RSD dosyaları varsa üstteki **Kayıt ekle** ile aynı projede birleştir.
3. Sekmeler:
   - **Harita**: uydu üzerinde katmanlar (derinlik, eş derinlik çizgileri, belirsizlik, zemin, değişim, notlar). Soldaki araçlarla **mesafe** ve **alan** ölçebilir, bir hat boyunca **derinlik profili** çizebilir, haritaya **not / işaret** koyabilirsin. Rotaya tıklayınca o noktanın sonar kesiti açılır.
   - **3B**: dip yüzeyini üç boyutlu gösterir; **yalnızca istediğin alanı** modellersin. *Haritadan alan seç* ile dikdörtgen ya da çokgen çiz; model sadece o şeklin içinde üretilir. Dikey büyütme, renk (derinlik / eğim / zemin / ölçüm-tahmin), kontur ve su yüzeyi ayarlanır; fareyle gezdikçe o noktanın derinliği okunur. **PNG**, **OBJ** ve **STL** (taban plakalı kapalı katı) olarak dışa aktarılır.
   - **Sonar**: kaydın tamamında gezinilen kesit görüntüleyici (çubuk, ←/→, boşluk = oynat). **Düzelt** ile yanlış bulunan dip çizgisini elle çizebilir, hatalı ping aralıklarını silebilirsin.
   - **Grafikler**: derinlik, hız, sıcaklık ve **kot–alan–hacim** eğrisi + tablosu.
   - **Analizler**: isteğe bağlı analizler (aşağıda); her kartın **?** düğmesi o analizin ne yaptığını anlatır, çalışan analiz **İptal** edilebilir.
   - **Dosyalar**: tüm görseller ve çıktı dosyaları; *İndir* Windows'un Kaydet penceresini açar.
4. **Rapor** menüsü kapaklı **PDF** raporu (firma adı ve logosu, imza alanları) ya da HTML raporu açar.
5. **Proje ayarları**: ses hızı düzeltmesi, batma payı, su yüzeyi kotu ve projedeki kayıtlar. Değişiklikten sonra çıkan **Yeniden hesapla** düğmesiyle tüm sonuçlar güncellenir.

| İsteğe bağlı analiz | Süre | Ne üretir |
|---|---|---|
| Zemin sınıflaması | ~2 dk | Göreli zemin sınıfları, sertlik / penetrasyon haritaları, numune noktaları (GPX) |
| Uydu, hacim ve rota | ~1 dk | Kıyı çizgisi, tüm su alanının hacmi, dip eğimi, kapsama, yeni tarama rotası (GPX); internet gerekir |
| Su kolonu ve dip taramaları | ~1 dk | Balık ve gaz kabarcığı izleri, kaya / nesne ve bitki örtüsü taraması (önce zemin sınıflaması) |
| Doğrulama ve kalibrasyon | ~5 sn | Saha derinlikleri / dip numuneleriyle karşılaştırma, RMSE, kalibrasyon ve sınıf adı önerisi |
| Değişim analizi | ~5 sn | Başka tarihteki taramayla dip kotu farkı, sediman birikimi / oyulma haritası, yıllık m³ |
| Mühendislik çıktıları | ~10 sn | Seçili koordinat sisteminde GeoTIFF, Shapefile, GeoJSON, KML, DXF (R12), XYZ; tek zip |
| Rapor | ~20 sn | Kapaklı PDF ve HTML rapor |

## Ayarlar

Sol alttaki **Ayarlar**: dil (Türkçe / English), uzunluk birimi (m / ft), kontur aralığı, derinlik renk paleti, mühendislik çıktılarının koordinat sistemi (WGS84 / UTM, **TUREF (ITRF96) / TM 3°**, ED50), yeni projeler için ölçüm varsayılanları, rapor için firma adı, hazırlayan ve logo.

**Hakkında** sürümü, lisansı ve kullanılan bileşenleri gösterir. Program açılışta yeni sürüm olup olmadığını denetler; yeni sürüm varsa **İndir ve kur** ile indirilip kurulur, projeler ve ayarlar korunur.

## Sorun olursa

Analiz hata verirse kartta anlaşılır bir açıklama çıkar. **⋯ → Hata raporu oluştur** program ve proje günlüklerini tek bir zip'te toplar (sonar kaydının kendisi eklenmez); bu dosyayı paylaşarak destek isteyebilirsin.

## Veriler nerede

Her kayıt `BAHR SONARVIEW\Projeler\<tarih-kimlik>\` altında saklanır: yüklenen dosyalar (`ham.RSD`, `ham_2.RSD`…), tüm çıktılar (`cozumleme\`), ayarlar (`parametreler.json`), elle düzeltmeler, notlar ve analiz günlüğü. Program ayarları `BAHR SONARVIEW\ayarlar.json` dosyasındadır.

## Sınırlar

- Yalnızca Garmin `.RSD`; kayıttaki aşağı bakan (DownVü) kanal kullanılır.
- Zemin, balık ve bitki sonuçları kalibre edilmemiş bir balık bulucudan elde edilen **göreli** sonuçlardır; kesin zemin tipi için dip numunesi gerekir (Doğrulama analizi).
- Yüzeyin ilk ~1,4 m'si (verici çınlaması) su kolonu taramalarında görülmez.
- Haritalar ve görseller metrik birimle üretilir; ft seçimi arayüzü ve raporu etkiler.

## Geliştirici notu

Kaynak kod `kaynak\` klasöründedir. Değişiklikten sonra yeniden derlemek için `derle.bat` (projedeki `.venv` Python ortamını kullanır; `Projeler`, `ayarlar.json` ve firma logosuna dokunmaz). Program `BAHR SONARVIEW.exe --motor <betik>` biçiminde kendini çağırarak analiz adımlarını ayrı süreçte çalıştırır. Sürüm numarası `kaynak\surum.py` içindedir.
