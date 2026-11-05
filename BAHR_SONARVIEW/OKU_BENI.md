# BAHR SONARVIEW

Garmin balık bulucu sonar kayıtları (`.RSD`) için masaüstü analiz programı. Kendi penceresinde çalışır; tarayıcı, Python ya da internet kurulumu gerektirmez (yalnızca uydu altlığı için internet kullanılır).

## Açmak

Bu klasördeki **`run.bat`** ya da **`BAHR SONARVIEW`** kısayoluna çift tıkla (ikisi de `BAHR SONARVIEW\BAHR SONARVIEW.exe`'yi açar).

- Masaüstüne kısayol için: `.exe`'ye sağ tıkla → *Daha fazla seçenek göster* → *Gönder* → *Masaüstü (kısayol oluştur)*.
- Program zaten açıksa ikinci kez açılmaz; açık pencereyi kullan.
- `BAHR SONARVIEW` klasörü taşınabilir: klasörün tamamını başka bir yere ya da başka bir Windows bilgisayara kopyalayabilirsin (içindeki `_internal` klasörüyle birlikte).

## Kullanım

1. **Yeni kayıt yükle**'ye tıkla ve Garmin cihazın hafıza kartındaki `Sonar*.RSD` dosyasını seç (ya da dosyayı pencereye sürükle).
2. **Temel analiz** kendiliğinden çalışır (~1 dk).
3. Sekmeler:
   - **Harita** – uydu üzerinde katmanlar; rotaya tıkla, o noktanın sonar kesiti açılır.
   - **Sonar** – kaydın tamamında gezinilen kesit görüntüleyici (çubuk, ←/→, boşluk = oynat).
   - **Grafikler** – derinlik, hız, sıcaklık; grafiğe tıkla, o anın kesitine git.
   - **Analizler** – isteğe bağlı analizler (aşağıda).
   - **Dosyalar** – görseller, CSV / GPX; *İndir* Windows'un Kaydet penceresini açar.
4. Üstteki **Rapor** düğmesi tek dosyalık raporu oluşturur ve varsayılan tarayıcıda açar (oradan PDF olarak kaydedilebilir). **Klasörü aç** tüm çıktıları Dosya Gezgini'nde açar.

| İsteğe bağlı analiz | Süre | Ne üretir |
|---|---|---|
| Zemin sınıflaması | ~2 dk | Göreli zemin sınıfları, sertlik / penetrasyon haritaları, numune noktaları (GPX) |
| Uydu, hacim ve rota | ~1 dk | Kıyı çizgisi, toplam hacim, dip eğimi, kapsama, yeni tarama rotası (GPX) — internet gerekir |
| Su kolonu ve dip taramaları | ~1 dk | Balık ve gaz kabarcığı izleri, kaya / nesne ve bitki örtüsü taraması (önce zemin sınıflaması) |
| Rapor | ~10 sn | Çalışmış analizlerin HTML raporu |

## Veriler nerede

Her kayıt `BAHR SONARVIEW\Projeler\<tarih-kimlik>\` altında saklanır: yüklenen dosya (`ham.RSD`), tüm çıktılar (`cozumleme\`) ve analiz günlüğü (`analiz_gunlugu.txt`). Proje silmek için programdaki çöp kutusu düğmesini kullan.

## Sınırlar

- Yalnızca Garmin `.RSD`; kayıttaki aşağı bakan (DownVü) kanal kullanılır.
- Zemin, balık ve bitki sonuçları kalibre edilmemiş bir balık bulucudan elde edilen **göreli** sonuçlardır; kesin zemin tipi için dip numunesi gerekir.
- Yüzeyin ilk ~1,4 m'si (verici çınlaması) su kolonu taramalarında görülmez.

## Geliştirici notu

Kaynak kod `kaynak\` klasöründedir. Değişiklikten sonra yeniden derlemek için `derle.bat` (projedeki `.venv` Python ortamını kullanır; `Projeler` klasörüne dokunmaz). Program `BAHR SONARVIEW.exe --motor <betik>` biçiminde kendini çağırarak analiz adımlarını ayrı süreçte çalıştırır.
