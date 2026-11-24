/* BAHR SONARVIEW - dil destegi (Turkce / English) ve yardim metinleri.
   Arayuz Turkce yazilir; DIL = "en" iken t() ve dilUygula() Ingilizce karsiligini kullanir. */
"use strict";
window.DIL = window.DIL || "tr";

const EN = {
  // ---- genel / kenar
  "Sonar analiz programı": "Sonar survey software", "Yeni kayıt yükle": "Load new recording", "Garmin .RSD dosyasını bırak ya da seç": "Drop or choose a Garmin .RSD file",
  "Projeler": "Projects", "Projelerde ara…": "Search projects…", "Projelerde ara": "Search projects", "Ayarlar": "Settings", "Yardım": "Help", "Hakkında": "About",
  "yeni": "new", "Yerel çalışır · veriler bu bilgisayarda kalır": "Runs locally · data stays on this computer", "Veriler bu bilgisayarda kalır": "Data stays on this computer",
  "Projeler klasörü": "Projects folder", "Henüz proje yok. İlk kaydını yükle.": "No projects yet. Load your first recording.", "Eşleşen proje yok.": "No matching project.",
  "kayıt": "recordings", "kontrol ediliyor…": "checking…", "Yükleme başarısız": "Upload failed", "Yükleme sırasında bağlantı koptu": "Connection lost during upload",
  "Yalnızca Garmin .RSD dosyaları destekleniyor": "Only Garmin .RSD files are supported",
  // ---- karsilama
  "Sonar kaydını yükle, gölün dibini gör.": "Load a sonar recording, see the bottom of the lake.",
  "Garmin balık bulucunun kartındaki": "Drop the", "Sonar*.RSD": "Sonar*.RSD",
  "dosyasını bırak. Derinlik haritası, sonar görüntüleri ve grafikler birkaç dakikada hazır; zemin, hacim, değişim analizi ve mühendislik çıktıları tek tıkla.":
    "file from your Garmin fish finder's card. Depth map, sonar images and charts are ready in minutes; bottom type, volume, change analysis and engineering deliverables in one click.",
  ".RSD dosyasını buraya bırak": "Drop the .RSD file here", "ya da tıklayıp seç": "or click to choose", "Derinlik haritası": "Depth map",
  "uydu üzerinde, eş derinlik çizgileriyle": "on satellite imagery, with contours", "Canlı sonar kesiti": "Live sonar section", "dip çizgisini elle düzelt": "edit the bottom line by hand",
  "Zemin, hacim, değişim": "Bottom, volume, change", "kot–alan–hacim, sediman birikimi": "elevation–area–capacity, sedimentation",
  "Mühendislik çıktıları": "Engineering deliverables", "TUREF/UTM, GeoTIFF, SHP, DXF, PDF": "TUREF/UTM, GeoTIFF, SHP, DXF, PDF",
  // ---- proje ust
  "Proje adı": "Project name", "Aynı projeye başka bir RSD kaydı ekle": "Add another RSD recording to this project", "Kayıt ekle": "Add recording",
  "Ölçüm parametreleri ve kayıtlar": "Survey parameters and recordings", "Proje ayarları": "Project settings", "Çıktı klasörünü Dosya Gezgini'nde aç": "Open output folder in Explorer",
  "Klasör": "Folder", "Rapor oluştur / aç": "Create / open report", "Rapor": "Report", "PDF raporu aç": "Open PDF report", "HTML raporu aç": "Open HTML report",
  "Raporu yeniden oluştur": "Regenerate report", "Diğer işlemler": "More actions", "Tüm analizleri yeniden hesapla": "Recompute all analyses",
  "Hata raporu oluştur": "Create error report", "Projeyi sil": "Delete project", "Sonuçlar güncel değil.": "Results are out of date.",
  "Ölçüm parametreleri, kayıtlar ya da elle düzeltmeler değişti.": "Survey parameters, recordings or manual edits have changed.", "Yeniden hesapla": "Recompute",
  "Kayıt analiz ediliyor": "Analysing recording", "Hazırlanıyor…": "Preparing…", "Hazırlanıyor": "Preparing", "İptal": "Cancel",
  "Harita": "Map", "Sonar": "Sonar", "Grafikler": "Charts", "Analizler": "Analyses", "Dosyalar": "Files",
  "batma payı": "draft", "ses hızı düzeltmeli": "sound-speed corrected", "Derinlik": "Depth", "Ortanca derinlik": "Median depth", "Haritalanan alan": "Mapped area",
  "Tahmini hacim": "Estimated volume", "bin m³": "thousand m³", "Ölçülen hacim": "Measured volume", "Kat edilen yol": "Distance travelled", "Kayıt süresi": "Recording time",
  "dk": "min", "Belirsizlik (ortanca)": "Uncertainty (median)", "Su sıcaklığı": "Water temperature",
  "Analiz tamamlanamadı.": "The analysis could not be completed.", "Analiz iptal edildi.": "The analysis was cancelled.", "Tekrar dene": "Try again", "Yeniden başlat": "Restart",
  "Sırada bekliyor": "Waiting in queue", "iş önde": "jobs ahead", "Temel analiz tamamlandı": "Basic analysis complete", "tamamlandı": "completed",
  "Harita verisi yüklenemedi: ": "Could not load map data: ",
  // ---- harita
  "Mesafe ölç": "Measure distance", "Alan ölç": "Measure area", "Derinlik profili çiz": "Draw depth profile", "Not / işaret ekle": "Add note / marker", "Çizimleri temizle": "Clear drawings",
  "Altlık": "Basemap", "Uydu": "Satellite", "Koyu": "Dark", "Yok": "None", "Katmanlar": "Layers", "Rotaya tıkla: o noktanın sonar kesiti açılır": "Click the track to open the sonar section at that point",
  "Sonar kesiti": "Sonar section", "Sonar sekmesinde aç →": "Open in Sonar tab →", "Kapat": "Close", "Derinlik profili": "Depth profile", "CSV indir": "Download CSV",
  "Tekne rotası": "Survey track", "Eş derinlik çizgileri": "Depth contours", "Belirsizlik": "Uncertainty", "Tüm su alanı (tahmin)": "Whole water area (estimate)",
  "Kıyı çizgisi": "Shoreline", "Önerilen yeni rota": "Suggested new route", "Zemin sınıfları": "Bottom classes", "Dip sertliği": "Bottom hardness", "Penetrasyon": "Penetration",
  "Numune noktaları": "Sampling points", "Dip değişimi": "Bottom change", "Balık izleri": "Fish tracks", "Sert nokta / nesne": "Hard spot / object", "Notlar ve işaretler": "Notes and markers",
  "çalıştırılınca açılır": "unlocks when run", "kilitli": "locked", "Başlangıç — hat 1": "Start — line 1", "Hat": "Line", "Balık izi": "Fish track", "Gaz kabarcığı": "Gas bubble",
  "Not": "Note", "Düzenle": "Edit", "Sil": "Delete", "Dip kotu değişimi": "Bottom elevation change", "oyulma": "erosion", "birikim": "deposition", "göreli": "relative",
  "Tahmini belirsizlik": "Estimated uncertainty", "yumuşak": "soft", "sert": "hard", "yüzeyden seker": "reflects at surface", "tortuya girer": "penetrates sediment",
  "Tahmini derinlik": "Estimated depth", "derinlik": "depth",
  "Tıklayarak noktalar ekle · çift tık ya da Enter: bitir · Esc: iptal": "Click to add points · double-click or Enter: finish · Esc: cancel",
  "Alanın köşelerine tıkla · çift tık ya da Enter: bitir · Esc: iptal": "Click the corners of the area · double-click or Enter: finish · Esc: cancel",
  "Profil hattının noktalarına tıkla · çift tık ya da Enter: profili çiz": "Click points along the profile line · double-click or Enter: draw profile",
  "Not eklemek istediğin yere tıkla": "Click where you want to add a note", "Alan": "Area", "çevre": "perimeter", "uzunluk": "length", "en derin": "deepest", "ortalama": "mean",
  "Ölçülen / ara değer": "Measured / interpolated", "Tahmin (uydu analizi)": "Estimate (satellite analysis)", "Mesafe": "Distance",
  "Not ekle": "Add note", "Notu düzenle": "Edit note", "Başlık": "Title", "örn. İskele, kaya, numune alındı": "e.g. jetty, rock, sample taken", "Açıklama": "Description",
  "Vazgeç": "Cancel", "Kaydet": "Save", "Notlar kaydedildi": "Notes saved", "Kesit alınamadı": "Could not load section",
  // ---- sonar
  "Oynat / durdur": "Play / pause", "Oynat": "Play", "Zaman": "Time", "Ping": "Ping", "Genişlik": "Width", "Dar (~12 sn)": "Narrow (~12 s)", "Orta (~25 sn)": "Medium (~25 s)",
  "Geniş (~50 sn)": "Wide (~50 s)", "Çok geniş (~1,5 dk)": "Very wide (~1.5 min)", "Palet": "Palette", "Bakır": "Copper", "Okyanus": "Ocean", "Sıcak": "Hot", "Gri": "Gray",
  "Dip çizgisini elle düzelt": "Edit the bottom line by hand", "Düzelt": "Edit", "Basılı tutup sürükleyerek doğru dip çizgisini çiz": "Press and drag to draw the correct bottom line",
  "Dip çiz": "Draw bottom", "Sürükleyerek hatalı ping aralığını işaretle": "Drag to mark a bad ping range", "Aralık sil": "Delete range",
  "Basılı tutup sürükle. Kaydedince analizleri yeniden hesapla.": "Press and drag. After saving, recompute the analyses.", "Geri al": "Undo", "Tümünü kaldır": "Remove all",
  "Kayıt içinde konum": "Position in recording", "Çubuğu sürükle ya da ←/→ tuşlarını kullan": "Drag the slider or use the ←/→ keys", "Tüm kayıt": "Whole recording",
  "tıkla: o ana git": "click: jump there", "Tüm kayıt — derinlik profili": "Whole recording — depth profile", "çizilen dip": "redrawn bottom", "silinen aralık": "deleted ranges",
  "kaydedilmedi": "not saved", "Çalışan analiz varken düzeltme yapılamaz.": "Edits are not possible while an analysis is running.",
  "Kaydedilmemiş düzeltmeler var. Kapatılsın mı?": "There are unsaved edits. Close anyway?", "Bu projedeki tüm elle düzeltmeler kaldırılsın mı?": "Remove all manual edits in this project?",
  "Kaydediliyor…": "Saving…", "Düzeltmeler kaydedildi. Haritaların güncellenmesi için 'Yeniden hesapla'yı kullanın.": "Edits saved. Use 'Recompute' to update the maps.",
  // ---- grafik
  "noktaya tıkla: sonar kesitine git": "click a point: go to sonar section", "Tekne hızı": "Boat speed", "Kot – alan – hacim": "Elevation – area – capacity",
  "Kayıt süresi (dk)": "Recording time (min)", "su yüzeyi kotu": "water surface elevation", "Alan (m²)": "Area (m²)", "Hacim (m³)": "Volume (m³)", "Kot": "Elevation",
  "Hacim": "Volume", "Toplam": "Total", "Tabloyu indir": "Download table",
  "tüm su alanı (uydudan kıyı çizgisiyle)": "whole water area (shoreline from satellite)", "yalnızca ölçülen alan": "measured area only",
  // ---- analizler
  "Temel analiz her yüklemede otomatik çalışır. Diğerleri isteğe bağlı: ihtiyacın olanı çalıştır, sonuçlar haritaya, rapora ve dosyalara eklenir.":
    "The basic analysis runs automatically on every upload. The others are optional: run what you need; results are added to the map, report and files.",
  "Temel analiz": "Basic analysis", "Zemin sınıflaması": "Bottom classification", "Uydu, hacim ve rota": "Satellite, volume and route",
  "Su kolonu ve dip taramaları": "Water column and bottom scans", "Doğrulama ve kalibrasyon": "Validation and calibration", "Değişim analizi": "Change analysis",
  "RSD dosyasını çözer; düzeltmeleri uygular. Rota, derinlik haritası, eş derinlik çizgileri, sonar görüntüleri, kot–alan–hacim tablosu ve belirsizlik haritası.":
    "Decodes the RSD file and applies corrections. Track, depth map, contours, sonar images, elevation–area–capacity table and uncertainty map.",
  "Dip yankısının şeklinden sertlik, penetrasyon ve sönümlenme ölçer; zemini 3 göreli sınıfa ayırır ve dip numunesi noktaları önerir (GPX).":
    "Measures hardness, penetration and decay from the shape of the bottom echo; splits the bottom into 3 relative classes and suggests sampling points (GPX).",
  "Uydu görüntüsünden kıyı çizgisini çıkarır; tüm su alanı için hacim, dip eğimi, kapsama ve eksik alanlar için yeni tarama rotası (GPX). İnternet gerekir.":
    "Extracts the shoreline from satellite imagery; volume of the whole water area, bottom slope, coverage and a new survey route for gaps (GPX). Needs internet.",
  "Su kolonunda balık ve gaz kabarcığı izleri, dipte kaya / batık nesne ve su bitkisi örtüsü taraması.": "Fish and gas-bubble tracks in the water column, rocks / debris on the bottom and aquatic vegetation.",
  "Çubukla ölçülen derinlikleri ve dip numunelerini sonarla karşılaştırır; doğruluk (RMSE) verir, kalibrasyon ve sınıf adları önerir.":
    "Compares rod-measured depths and grab samples with the sonar; reports accuracy (RMSE) and suggests a calibration and class names.",
  "Aynı göletin başka tarihteki taramasıyla karşılaştırır: dip kotu değişimi, sediman birikimi / oyulma haritası, yıllık m³.":
    "Compares with a survey of the same pond on another date: bottom elevation change, deposition / erosion map, m³ per year.",
  "Seçilen koordinat sisteminde GeoTIFF, Shapefile, GeoJSON, KML (Google Earth), DXF (AutoCAD / NetCAD) ve XYZ dosyaları; tek zip.":
    "GeoTIFF, Shapefile, GeoJSON, KML (Google Earth), DXF (AutoCAD / NetCAD) and XYZ files in the selected coordinate system; one zip.",
  "Çalışmış tüm analizleri kapak, firma bilgisi ve imza alanıyla tek rapora toplar: PDF ve HTML.": "Collects all completed analyses into one report with cover, company details and signature block: PDF and HTML.",
  "Sırada": "Queued", "Çalışıyor": "Running", "Tamamlandı": "Completed", "Hata": "Error", "İptal edildi": "Cancelled", "Çalışmadı": "Not run",
  "Çalıştır": "Run", "Yeniden çalıştır": "Run again", "Yeniden oluştur": "Regenerate", "süre": "time", "Önce": "First", "Önce CSV yükleyin": "Upload a CSV first", "Önce proje seçin": "Choose a project first",
  "Bu ne demek?": "What does this mean?", "Haritalanan": "Mapped", "Toplam hacim": "Total volume", "Ölçülen": "Measured", "Yeni rota": "New route", "hat": "lines",
  "Dip eğimi": "Bottom slope", "yok": "none", "Sert nokta": "Hard spot", "Bitki kaplama": "Vegetation cover", "Ortalama fark": "Mean difference", "Zemin uyumu": "Bottom agreement",
  "Numune": "Samples", "Net": "Net", "Yıllık": "Per year", "Birikim": "Deposition", "Oyulma": "Erosion", "Koordinat": "Coordinates", "Dosya": "Files",
  "Şablonu indir": "Download template", "CSV yükle": "Upload CSV", "Yeni CSV yükle": "Upload new CSV", "Kalibrasyon önerisi": "Suggested calibration", "Batma payı": "Transducer draft",
  "ses hızı": "sound speed", "Zemin sınıflarına numune adlarını ver": "Name bottom classes after the samples", "Uygula ve yeniden hesapla": "Apply and recompute",
  "Karşılaştırılacak tarama": "Survey to compare with", "— proje seç —": "— choose project —", "Koordinat sistemi": "Coordinate system", "ZIP'i kaydet": "Save ZIP",
  "Klasörü aç": "Open folder", "PDF'i aç": "Open PDF", "HTML'i aç": "Open HTML", "Doğrulama verisi yüklendi": "Validation data uploaded",
  "Kalibrasyon uygulandı; analizler yeniden hesaplanıyor": "Calibration applied; recomputing analyses", "Uygulanacak öneri seçilmedi": "No suggestion selected",
  "Koordinat sistemi kaydedildi": "Coordinate system saved", "İptal ediliyor…": "Cancelling…", "Analizler yeniden hesaplanıyor": "Recomputing analyses",
  "Rapor hazırlanıyor…": "Preparing report…", "Rapor hazırlanıyor; bitince bu menüden açılır": "Preparing report; open it from this menu when done",
  "projesi ve tüm çıktıları kalıcı olarak silinsin mi?": "— delete this project and all its outputs permanently?", "Proje silindi": "Project deleted",
  "Hata raporu kaydedildi: ": "Error report saved: ", "Kaydedildi: ": "Saved: ",
  // adim etiketleri (sunucudan)
  "Dosya çözülüyor": "Decoding file", "Düzeltmeler uygulanıyor": "Applying corrections", "Sonar görüntüleri ve grafikler": "Sonar images and charts",
  "Derinlik ızgarası": "Depth grid", "Harita katmanları": "Map layers", "Hacim tablosu ve belirsizlik": "Volume table and uncertainty", "Dip yankıları inceleniyor": "Examining bottom echoes",
  "Numune noktaları seçiliyor": "Selecting sampling points", "Uydu görüntüsü": "Satellite imagery", "Hacim, eğim, kapsama, rota": "Volume, slope, coverage, route",
  "Su kolonu okunuyor": "Reading water column", "Kaya / nesne taraması": "Rock / object scan", "Bitki örtüsü taraması": "Vegetation scan", "Balık ve kabarcık taraması": "Fish and bubble scan",
  "Saha verisiyle karşılaştırılıyor": "Comparing with field data", "Taramalar karşılaştırılıyor": "Comparing surveys", "GeoTIFF, Shapefile, KML, DXF hazırlanıyor": "Preparing GeoTIFF, Shapefile, KML, DXF",
  "Rapor hazırlanıyor": "Preparing report", "PDF oluşturuluyor": "Creating PDF",
  // ---- dosyalar
  "Sonar görüntüleri ve grafikler ": "Sonar images and charts", "Kot–alan–hacim ve belirsizlik": "Elevation–area–capacity and uncertainty", "Uydu üzerinde haritalar": "Maps on satellite imagery",
  "Zemin sınıflaması ve numune": "Bottom classification and samples", "Hacim, eğim ve rota": "Volume, slope and route", "Saha doğrulaması": "Field validation",
  "Sert nokta taraması": "Hard-spot scan", "Bitki örtüsü": "Vegetation", "Balık ve kabarcık": "Fish and bubbles", "Henüz dosya yok.": "No files yet.", "İndir": "Download",
  // ---- ayarlar
  "Genel": "General", "Dil": "Language", "Uzunluk birimi": "Length unit", "Metre (m)": "Metres (m)", "Fit (ft)": "Feet (ft)", "Açılışta güncellemeleri denetle": "Check for updates at start-up",
  "Kontur aralığı": "Contour interval", "Otomatik": "Automatic", "Derinlik renk paleti": "Depth colour palette", "Yeni projeler için ölçüm varsayılanları": "Survey defaults for new projects",
  "Ses hızı düzeltmesi": "Sound speed correction", "Kapalı": "Off", "Su sıcaklığından hesapla": "Compute from water temperature", "Elle gir": "Enter manually",
  "Cihazın varsaydığı ses hızı (m/s)": "Sound speed assumed by the device (m/s)", "Elle ses hızı (m/s)": "Manual sound speed (m/s)", "Batma payı (m)": "Transducer draft (m)",
  "Firma / kurum adı": "Company / organisation", "Hazırlayan": "Prepared by", "Logo yok": "No logo", "Firma logosu seç": "Choose company logo", "Kaldır": "Remove",
  "Harita ve ölçüm ayarları, analizler yeniden hesaplanınca uygulanır.": "Map and survey settings apply when analyses are recomputed.",
  "Ayarlar kaydedildi": "Settings saved", "Ayarlar kaydedildi. Haritaların yeni ayarlarla çizilmesi için 'Yeniden hesapla'yı kullanın.": "Settings saved. Use 'Recompute' to redraw the maps with the new settings.",
  "Mavi": "Blue", "Plazma": "Plasma", "Sarı-mavi": "Yellow-blue", "Arazi": "Terrain",
  "WGS84 enlem / boylam (EPSG:4326)": "WGS84 latitude / longitude (EPSG:4326)", "WGS84 / UTM (6°)": "WGS84 / UTM (6°)", "TUREF (ITRF96) / TM 3°": "TUREF (ITRF96) / TM 3°",
  "ED50 / TM 3°": "ED50 / TM 3°", "ED50 / UTM (6°)": "ED50 / UTM (6°)",
  "Logo dosyası bir resim (PNG / JPG) olmalı.": "The logo must be an image (PNG / JPG).",
  // ---- proje ayarlari
  "Kayıtlar": "Recordings", "Çıkar": "Remove", "Aynı göletin birden çok RSD dosyası tek haritada birleştirilir. Kayıt eklenince elle düzeltmeler sıfırlanır.":
    "Several RSD files of the same pond are merged into one map. Adding a recording resets manual edits.",
  "Ölçüm parametreleri": "Survey parameters", "Su yüzeyi kotu (m)": "Water surface elevation (m)", "Değişiklikten sonra 'Yeniden hesapla' gerekir.": "'Recompute' is needed after changes.",
  "Bu kayıt projeden çıkarılsın mı? Analizler yeniden hesaplanır.": "Remove this recording from the project? Analyses will be recomputed.", "Kayıt çıkarıldı": "Recording removed",
  "Proje ayarları kaydedildi": "Project settings saved", "Kayıt ekleniyor…": "Adding recording…", "Kayıt eklendi; analizler yeniden hesaplanıyor": "Recording added; recomputing analyses",
  "Çalışan analiz varken kayıt eklenemez; bitmesini bekleyin ya da iptal edin.": "A recording cannot be added while an analysis is running; wait or cancel it.",
  "Çalışan analiz varken kayıt çıkarılamaz.": "A recording cannot be removed while an analysis is running.", "Projede en az bir kayıt kalmalı.": "The project must keep at least one recording.",
  "Çalışan analiz varken düzeltme kaydedilemez.": "Edits cannot be saved while an analysis is running.", "Çalışan analiz varken proje silinemez": "A project cannot be deleted while an analysis is running",
  // ---- hakkinda / guncelleme
  "Sürüm": "Version", "Telif": "Copyright", "Web": "Web", "Lisans": "Licence", "Yeni sürüm hazır": "New version available", "Ayrıntılar": "Details", "Program güncel.": "You have the latest version.",
  "Güncellemeleri denetle": "Check for updates", "Kullanılan açık kaynak bileşenler": "Open-source components", "Bileşen": "Component", "Veri klasörü": "Data folder",
  "Tüm hakları saklıdır. Bu yazılımın lisansı henüz belirlenmemiştir.": "All rights reserved. A licence for this software has not been chosen yet.",
  "Esri World Imagery (uydu altlığı)": "Esri World Imagery (satellite basemap)", "Esri kullanım koşulları": "Esri terms of use", "CARTO / OpenStreetMap (koyu altlık)": "CARTO / OpenStreetMap (dark basemap)",
  "ODbL / CARTO koşulları": "ODbL / CARTO terms", "hazır": "is available", "kullandığınız": "you have", "Güncelleme": "Update", "Kullandığınız sürüm": "Your version", "Yeni sürüm": "New version",
  "Sürüm notu yok.": "No release notes.", "Projeleriniz ve ayarlarınız güncellemeden etkilenmez.": "Your projects and settings are not affected by the update.",
  "Sürüm sayfası": "Release page", "İndir ve kur": "Download and install", "İndirme sayfasını aç": "Open download page", "İndiriliyor": "Downloading",
  "Çalışan analizler durdurulacak. Program kapanıp güncellenerek yeniden açılsın mı?": "Running analyses will be stopped. Close, update and restart the program?",
  "Kuruluyor; program kapanıp yeniden açılacak…": "Installing; the program will close and reopen…",
  "Güncelleme sunucusuna ulaşılamadı (URLError)": "Could not reach the update server",
  // ---- yardim
  "Konu ara…": "Search topics…", "Tamam": "OK", "Klavye": "Keyboard", "sonarda ilerle": "move through sonar", "boşluk": "space", "oynat": "play", "düzeltmeyi geri al": "undo edit", "kapat": "close",
  "Bırak, analiz başlasın": "Drop to start the analysis", "Sunucuya bağlanılamadı": "Could not connect to the server",
  // ---- sunucu / motor mesajlari
  "Önce doğrulama verisini (CSV) yükleyin.": "Upload the validation data (CSV) first.", "Önce karşılaştırılacak projeyi seçin.": "Choose the project to compare with first.",
  "Önce doğrulama analizini çalıştırın.": "Run the validation analysis first.", "Doğrulama dosyası çok büyük": "The validation file is too large", "Düzeltme verisi okunamadı": "Could not read the edit data",
  "Profil hattı okunamadı": "Could not read the profile line", "Profil için en az iki nokta gerekli": "A profile needs at least two points",
  "Profil için temel analizin bu sürümle yeniden çalıştırılması gerekiyor (Yeniden hesapla).": "Profiles need the basic analysis to be re-run with this version (Recompute).",
  "İndirilecek güncelleme bulunamadı": "No update to download", "Otomatik kurulum yalnızca paketlenmiş programda yapılabilir.": "Automatic installation works only in the packaged program.",
  "Önce güncellemeyi indirin.": "Download the update first.", "Güncelleme paketi beklenen yapıda değil.": "The update package does not have the expected structure.",
  "İnternet bağlantısı gerekli: uydu görüntüsü indirilemedi. Bağlantınızı kontrol edip tekrar deneyin.": "An internet connection is needed: satellite imagery could not be downloaded. Check your connection and try again.",
  "Bilgisayarın belleği bu kayıt için yetmedi. Diğer programları kapatıp tekrar deneyin; çok uzun kayıtları cihazda bölerek kaydetmek de işe yarar.": "Not enough memory for this recording. Close other programs and try again; splitting very long recordings on the device also helps.",
  "Bir çıktı dosyası başka bir programda açık olduğu için yazılamadı. Açık görsel / Excel dosyalarını kapatıp tekrar deneyin.": "An output file could not be written because it is open in another program. Close open images / Excel files and try again.",
  "Diskte yer kalmadı. Yer açıp tekrar deneyin.": "The disk is full. Free some space and try again.",
  "Kayıtta GPS konumu yok; harita üretilemez. Cihazın GPS'i açıkken kaydedilmiş bir dosya yükleyin": "The recording has no GPS position, so no map can be made. Load a file recorded with the device's GPS on",
  "Kayıtta derinlik okuması yok denecek kadar az; cihaz kayıt sırasında dibi görmemiş olabilir": "The recording has almost no depth readings; the device may not have seen the bottom",
  "Seçilen projede derinlik ızgarası yok. O projede temel analizi (bu sürümle) yeniden çalıştırın.": "The selected project has no depth grid. Re-run its basic analysis (with this version).",
  "İki taramanın ortak ölçülen alanı çok küçük; aynı gölete ait olduklarından emin olun.": "The two surveys hardly overlap; make sure they cover the same pond.",
  "Doğrulama verisi yüklenmemiş. Önce şablona göre hazırlanmış CSV dosyasını yükleyin.": "No validation data. Upload a CSV prepared according to the template first.",
  "Ölçüm hattına 3 m'den yakın en az 2 derinlik noktası gerekli": "At least 2 depth points within 3 m of the survey track are needed",
  "Yükleniyor": "Loading",
  "3B": "3D", "3B topografya için alan seç": "Select an area for 3D topography", "3B alanı": "3D area", "Alan": "Area",
  "Sürükle: döndür · Sağ tuş ya da Shift+sürükle: kaydır · Tekerlek: yakınlaştır · Çift tık: sıfırla": "Drag: rotate · Right button or Shift+drag: pan · Wheel: zoom · Double-click: reset",
  "Tüm ölçülen alan": "Whole measured area", "Tüm alan": "Whole area", "Dikdörtgen": "Rectangle", "Çokgen": "Polygon", "köşe": "corners",
  "Haritadan alan seç": "Select area on map", "Tahmini (uydu) alanı dahil et": "Include estimated (satellite) area", "Çözünürlük": "Resolution",
  "Dikey büyütme": "Vertical exaggeration", "dikey büyütme": "vertical exaggeration", "Renk": "Colour", "Ölçüm / tahmin": "Measured / estimated", "Zemin sınıfı": "Bottom class",
  "Eş derinlik çizgileri": "Depth contours", "Su yüzeyi": "Water surface", "Eğik": "Oblique", "Üstten": "Top", "Yandan": "Side", "Seçilen alan": "Selected area",
  "Dışa aktar": "Export", "OBJ / STL kapalı katı model olarak (taban plakalı) verilir; 3B yazıcı ve CAD için.": "OBJ / STL are exported as a closed solid (with a base plate) for 3D printing and CAD.",
  "3B yüzey hazırlanıyor…": "Preparing 3D surface…", "Henüz yüzey yok": "No surface yet", "En derin": "Deepest", "En sığ": "Shallowest", "Ortalama": "Mean", "Kapsam": "Extent",
  "doğu": "east", "kuzey": "north", "ölçüm": "measured", "Ölçüm": "Measured", "Veri kaynağı": "Data source", "Kontur aralığı": "Contour interval",
  "Bu bilgisayarda 3B görüntüleme (WebGL) kullanılamıyor.": "3D display (WebGL) is not available on this computer.",
  "Seçilen alan 3B yüzey için çok dar ya da parçalı.": "The selected area is too narrow or fragmented for a 3D surface.",
  "Önce bir 3B yüzey oluşturun": "Create a 3D surface first", "Alan için en az üç köşe gerekli": "At least three corners are needed for an area",
  "3B alan: dikdörtgenin iki karşıt köşesine tıkla · Esc: iptal": "3D area: click two opposite corners of the rectangle · Esc: cancel",
  "3B alan: alanın köşelerine tıkla · çift tık ya da Enter: bitir · Esc: iptal": "3D area: click the corners of the area · double-click or Enter: finish · Esc: cancel",
  "Seçilen alanda derinlik verisi yok. Ölçüm hattının geçtiği bir alan seçin ya da 'tahmini alanı dahil et'i açın.": "There is no depth data in the selected area. Choose an area the survey track crosses, or turn on 'include estimated area'.",
  "Seçilen alan çok küçük; en az birkaç metrelik bir alan seçin.": "The selected area is too small; choose an area at least a few metres across.",
  "Bu projede 3B yüzey üretilecek derinlik verisi yok.": "This project has no depth data to build a 3D surface from.",
  "Bu özellik için temel analizin bu sürümle yeniden çalıştırılması gerekiyor (Yeniden hesapla).": "This feature needs the basic analysis to be re-run with this version (Recompute).",
  "Desteklenmeyen dosya türü": "Unsupported file type", "Otomatik": "Automatic",
  "Geç ›": "Skip ›",
  "Açılış animasyonunu göster": "Show start-up animation",
  "Su yüzeyi kotu yalnızca bir projede girilmiş; iki tarihte su seviyesi aynı kabul edildi.": "The water surface elevation was entered in only one project; equal water levels were assumed.",
  "Su yüzeyi kotu girilmediği için iki tarihte su seviyesi aynı kabul edildi.": "No water surface elevation was entered, so equal water levels were assumed.",
};

function t(s, d) {
  let r = window.DIL === "en" && s != null ? (EN[s] ?? EN[String(s).trim()] ?? s) : s;
  if (d) r = String(r).replace(/\{(\w+)\}/g, (_, k) => d[k] ?? "");
  return r;
}

/* Sayfadaki sabit metinleri cevir (metin dugumleri + title / placeholder / aria-label) */
function dilUygula(kok) {
  if (window.DIL !== "en" || !kok) return;
  const w = document.createTreeWalker(kok, NodeFilter.SHOW_TEXT, { acceptNode: n => n.parentElement && !/^(SCRIPT|STYLE|TEXTAREA|CODE|PRE)$/.test(n.parentElement.tagName) ? 1 : 2 });
  const d = [];
  while (w.nextNode()) d.push(w.currentNode);
  for (const n of d) {
    const s = n.nodeValue.trim();
    if (s && EN[s]) n.nodeValue = n.nodeValue.replace(s, EN[s]);
  }
  kok.querySelectorAll("[title],[placeholder],[aria-label]").forEach(el => {
    for (const a of ["title", "placeholder", "aria-label"]) { const v = el.getAttribute(a); if (v && EN[v.trim()]) el.setAttribute(a, EN[v.trim()]); }
  });
}

/* ------------------------------------------------------------------ yardim metinleri */
window.YARDIM = {
  baslangic: { tr: { baslik: "Başlarken", metin: `<ol><li>Garmin cihazın hafıza kartındaki <code>Sonar*.RSD</code> dosyasını <b>Yeni kayıt yükle</b> ile seç ya da pencereye sürükle.</li>
      <li><b>Temel analiz</b> kendiliğinden çalışır (~1 dk): rota, derinlik haritası, sonar görüntüleri, kot–alan–hacim tablosu, belirsizlik.</li>
      <li><b>Analizler</b> sekmesinden ihtiyacın olanları çalıştır; sonuçlar haritaya, rapora ve <b>Dosyalar</b>'a eklenir.</li>
      <li>Aynı göletin başka RSD dosyaları varsa <b>Kayıt ekle</b> ile tek projede birleştir.</li>
      <li>Rapor menüsünden kapaklı PDF raporu al; <b>Mühendislik çıktıları</b> ile CBS / CAD dosyalarını üret.</li></ol>` },
    en: { baslik: "Getting started", metin: `<ol><li>Choose the <code>Sonar*.RSD</code> file from your Garmin's memory card with <b>Load new recording</b>, or drag it onto the window.</li>
      <li>The <b>basic analysis</b> runs automatically (~1 min): track, depth map, sonar images, elevation–area–capacity table, uncertainty.</li>
      <li>Run what you need from the <b>Analyses</b> tab; results are added to the map, the report and <b>Files</b>.</li>
      <li>If you have more RSD files of the same pond, merge them into one project with <b>Add recording</b>.</li>
      <li>Get a PDF report with cover page from the Report menu; produce GIS / CAD files with <b>Engineering deliverables</b>.</li></ol>` } },
  temel: { grup: "analiz", tr: { baslik: "Temel analiz", metin: `<p>RSD dosyası çözülür, aşağı bakan (DownVü) kanaldaki her ping'in derinliği, konumu, hızı ve su sıcaklığı okunur. Kısa ve kopuk derinlik bölümleri (cihazın ikinci yankıyı dip sanması gibi) elenir, ~2 saniyelik kayan medyanla gürültü azaltılır.</p>
      <p>Ardından 1 m'lik derinlik ızgarası üretilir: eş derinlik çizgileri, kot–alan–hacim tablosu ve belirsizlik haritası bu ızgaradan hesaplanır. Proje ayarlarındaki <b>ses hızı</b>, <b>batma payı</b> ve <b>elle düzeltmeler</b> bu adımda uygulanır.</p>` },
    en: { baslik: "Basic analysis", metin: `<p>The RSD file is decoded and the depth, position, speed and water temperature of each ping on the down-looking (DownVü) channel are read. Short, isolated depth segments (e.g. the device mistaking the second echo for the bottom) are removed and noise is reduced with a ~2 s running median.</p>
      <p>A 1 m depth grid is then produced; contours, the elevation–area–capacity table and the uncertainty map are computed from it. The <b>sound speed</b>, <b>transducer draft</b> and <b>manual edits</b> from the project settings are applied in this step.</p>` } },
  zemin: { grup: "analiz", tr: { baslik: "Zemin sınıflaması", metin: `<p>Ses dibe çarptığında dönen yankının <b>şekli</b> zemin hakkında bilgi verir:</p>
      <ul><li><b>Sertlik</b>: dip yankısının tepe gücü. Sert, sıkı zemin (kum, çakıl, kaya) sesi güçlü yansıtır.</li>
      <li><b>Penetrasyon</b>: tepeden sonraki "kuyruk". Yumuşak çamurda ses tortunun içine girer, yankı uzun ve sönük olur.</li>
      <li><b>Sönümlenme</b>: kuyruğun ne kadar hızlı söndüğü.</li></ul>
      <p>Bu ölçüler 10 m ölçeğinde yumuşatılıp kümelenir ve 3 <b>göreli</b> sınıf çıkar. Cihaz kalibre olmadığından sınıflar "bu gölette daha yumuşak / daha sert" demektir; kesin zemin tipi için önerilen noktalardan <b>dip numunesi</b> alıp <b>Doğrulama</b> analizine yükleyin.</p>` },
    en: { baslik: "Bottom classification", metin: `<p>The <b>shape</b> of the echo returned by the bottom tells us about the substrate:</p>
      <ul><li><b>Hardness</b>: peak strength of the bottom echo. Hard, firm bottoms (sand, gravel, rock) reflect strongly.</li>
      <li><b>Penetration</b>: the "tail" after the peak. In soft mud the sound enters the sediment, so the echo is long and weak.</li>
      <li><b>Decay</b>: how quickly the tail fades.</li></ul>
      <p>These are smoothed at a 10 m scale and clustered into 3 <b>relative</b> classes. Because the device is not calibrated, classes mean "softer / harder in this pond"; for the actual substrate take <b>grab samples</b> at the suggested points and upload them to the <b>Validation</b> analysis.</p>` } },
  uydu: { grup: "analiz", tr: { baslik: "Uydu, hacim ve rota", metin: `<p>Uydu görüntüsünde teknenin geçtiği su piksellerinin rengi öğrenilir ve göletin tamamı (kıyı çizgisi) çıkarılır. Ölçülmeyen kıyı şeridi, kıyıda 0 m ya da 0,5 m derinlik varsayımıyla ara değerlenir; böylece <b>tüm göletin hacmi</b> bir aralık olarak verilir.</p>
      <p>Ayrıca dip eğimi ve pürüzlülüğü, rotanın kapsadığı alan ve eksik bölgeleri dolduracak <b>yeni tarama rotası</b> (Garmin'e yüklenebilir GPX) üretilir. İnternet bağlantısı gerekir.</p>` },
    en: { baslik: "Satellite, volume and route", metin: `<p>The colour of the water pixels crossed by the boat is learnt from satellite imagery and the whole pond (shoreline) is extracted. The unmeasured shore strip is interpolated assuming 0 m or 0.5 m depth at the shore, so the <b>volume of the whole pond</b> is given as a range.</p>
      <p>Bottom slope and roughness, survey coverage and a <b>new survey route</b> covering the gaps (GPX for the Garmin) are also produced. Needs internet.</p>` } },
  taramalar: { grup: "analiz", tr: { baslik: "Su kolonu ve dip taramaları", metin: `<p>Su kolonunda dipten ayrı duran güçlü, kısa yankılar <b>balık</b>; yukarı doğru eğik izler <b>gaz kabarcığı</b> olarak işaretlenir. Dipte çevresinden belirgin sert ve yükselen yankılar <b>kaya / batık nesne</b> adayıdır. Dibin hemen üstünde süreklilik gösteren yankı <b>su bitkisi</b> örtüsü olarak tahmin edilir.</p>
      <p>Vericinin çınlaması nedeniyle yüzeyin ilk ~1,4 m'si görülmez. Sonuçlar göreli ve kalibre değildir.</p>` },
    en: { baslik: "Water column and bottom scans", metin: `<p>Strong, short echoes in the water column, separate from the bottom, are marked as <b>fish</b>; upward-slanting tracks as <b>gas bubbles</b>. Hard echoes standing out from their surroundings on the bottom are <b>rock / object</b> candidates. Continuous echo just above the bottom is estimated as <b>vegetation</b>.</p>
      <p>The first ~1.4 m below the surface are not visible because of transducer ringdown. Results are relative and uncalibrated.</p>` } },
  dogrulama: { grup: "analiz", tr: { baslik: "Doğrulama ve kalibrasyon", metin: `<p>Sahada çubuk / iskandille ölçtüğün derinlikleri ve aldığın dip numunelerini bir CSV dosyasına yaz (<b>Şablonu indir</b>): <code>nokta; enlem; boylam; derinlik_m; zemin</code>. Konum yerine seçili koordinat sisteminde <code>x; y</code> de kullanılabilir.</p>
      <ul><li><b>Derinlik</b>: ölçüm hattına 3 m'den yakın noktalar sonarla karşılaştırılır; ortalama fark, standart sapma ve <b>RMSE</b> verilir. Sabit fark batma payına, orana bağlı fark ses hızına çevrilerek <b>kalibrasyon</b> önerilir.</li>
      <li><b>Zemin</b>: her numunenin düştüğü sonar sınıfı bulunur; her sınıfa en çok rastlanan numune adı önerilir ("Sınıf 1 = çamur").</li></ul>
      <p><b>Uygula ve yeniden hesapla</b> önerileri proje ayarlarına yazar ve analizleri yeniler.</p>` },
    en: { baslik: "Validation and calibration", metin: `<p>Write the depths you measured with a rod / lead line and your grab samples into a CSV (<b>Download template</b>): <code>nokta; enlem; boylam; derinlik_m; zemin</code> (point; latitude; longitude; depth_m; substrate). <code>x; y</code> in the selected coordinate system also work.</p>
      <ul><li><b>Depth</b>: points within 3 m of the survey track are compared with the sonar; mean difference, standard deviation and <b>RMSE</b> are reported. A constant offset is turned into a draft correction and a proportional error into a sound-speed correction (<b>calibration</b>).</li>
      <li><b>Bottom</b>: the sonar class at each sample is found and each class is given the most frequent sample name ("Class 1 = mud").</li></ul>
      <p><b>Apply and recompute</b> writes the suggestions into the project settings and refreshes the analyses.</p>` } },
  degisim: { grup: "analiz", tr: { baslik: "Değişim analizi (sediman birikimi)", metin: `<p>Aynı göletin farklı tarihlerdeki iki taraması üst üste konur. Her 1 m hücrede <b>dip kotu</b> = su yüzeyi kotu − derinlik hesaplanır ve farkı alınır:</p>
      <ul><li><b>+</b> (kırmızı): dip yükselmiş → <b>sediman birikimi</b></li><li><b>−</b> (mavi): dip derinleşmiş → oyulma / tarama</li></ul>
      <p>±10 cm'den küçük farklar ölçüm belirsizliği içinde sayılır. Birikim, oyulma ve net hacim (m³) ile tarihler arası süreye bölünmüş <b>yıllık hız</b> verilir.</p>
      <p class="not">Önemli: Su seviyesi iki tarihte farklıysa iki projede de <b>Su yüzeyi kotu</b>nu aynı referansla girin; aksi halde su seviyesi farkı birikim gibi görünür.</p>` },
    en: { baslik: "Change analysis (sedimentation)", metin: `<p>Two surveys of the same pond from different dates are overlaid. In every 1 m cell the <b>bottom elevation</b> = water surface elevation − depth is computed and differenced:</p>
      <ul><li><b>+</b> (red): bottom rose → <b>deposition</b></li><li><b>−</b> (blue): bottom deepened → erosion / dredging</li></ul>
      <p>Differences below ±10 cm are within measurement uncertainty. Deposition, erosion and net volume (m³) and the <b>rate per year</b> are reported.</p>
      <p class="not">Important: if the water level differed between the dates, enter the <b>water surface elevation</b> in both projects on the same datum; otherwise the level difference looks like deposition.</p>` } },
  disari: { grup: "analiz", tr: { baslik: "Mühendislik çıktıları", metin: `<p>Seçili koordinat sisteminde (Ayarlar → Mühendislik çıktıları) tek zip:</p>
      <ul><li><b>GeoTIFF</b>: 1 m derinlik ve kot ızgarası (ölçülen alan ve varsa tüm su alanı)</li>
      <li><b>Shapefile</b> (.prj ile): eş derinlik çizgileri, rota, ölçüm noktaları, zemin, numune, notlar…</li>
      <li><b>DXF (R12)</b>: AutoCAD / NetCAD için 3B eş derinlik çizgileri (Z = kot), etiketler, noktalar</li>
      <li><b>KML</b> (Google Earth), <b>GeoJSON</b>, <b>XYZ / CSV</b></li></ul>
      <p>Z değerleri <b>kot</b>tur: su yüzeyi kotu − derinlik. Su yüzeyi kotunu proje ayarlarından girin.</p>` },
    en: { baslik: "Engineering deliverables", metin: `<p>One zip in the selected coordinate system (Settings → Engineering deliverables):</p>
      <ul><li><b>GeoTIFF</b>: 1 m depth and elevation grid (measured area and, if available, the whole water area)</li>
      <li><b>Shapefile</b> (with .prj): contours, track, survey points, bottom classes, samples, notes…</li>
      <li><b>DXF (R12)</b>: 3D contours for AutoCAD / NetCAD (Z = elevation), labels, points</li>
      <li><b>KML</b> (Google Earth), <b>GeoJSON</b>, <b>XYZ / CSV</b></li></ul>
      <p>Z values are <b>elevations</b>: water surface elevation − depth. Enter the water surface elevation in the project settings.</p>` } },
  rapor: { grup: "analiz", tr: { baslik: "Rapor", metin: `<p>Kapak sayfası (firma adı ve logosu, proje, tarih, hazırlayan), Hazırlayan / Kontrol eden / Onaylayan imza alanları, özet ve çalışmış her analizin bölümünü içeren rapor. <b>PDF</b> (Microsoft Edge ile, sayfa numaralı A4) ve tek dosyalık <b>HTML</b> olarak üretilir.</p>
      <p>Firma adı, hazırlayan ve logo <b>Ayarlar → Rapor</b>'dan girilir. Rapor dili ve uzunluk birimi program ayarlarını izler.</p>` },
    en: { baslik: "Report", metin: `<p>A report with a cover page (company name and logo, project, date, prepared by), Prepared / Checked / Approved signature blocks, a summary and a section for each completed analysis. Produced as <b>PDF</b> (A4 with page numbers, via Microsoft Edge) and single-file <b>HTML</b>.</p>
      <p>Company, preparer and logo are set in <b>Settings → Report</b>. Report language and length unit follow the program settings.</p>` } },
  hacim_tablosu: { grup: "terim", tr: { baslik: "Kot – alan – hacim tablosu", metin: `<p>Baraj ve gölet işlerinin standart çıktısı: su seviyesi her kotta olsaydı <b>su yüzeyi alanı</b> ve <b>depolanan hacim</b> ne olurdu? Her 1 m hücrenin dip kotu (su yüzeyi kotu − derinlik) üzerinden hesaplanır.</p>
      <p>Uydu analizi yapıldıysa tüm su alanı, yapılmadıysa yalnızca ölçülen alan kullanılır. Gerçek kotlar için proje ayarlarına <b>su yüzeyi kotunu</b> girin; girilmezse su yüzeyi 0 kabul edilir ve kotlar negatif derinlik olarak görünür.</p>` },
    en: { baslik: "Elevation – area – capacity table", metin: `<p>The standard deliverable for dams and ponds: if the water stood at a given elevation, what would the <b>water surface area</b> and <b>stored volume</b> be? Computed from the bottom elevation (water surface elevation − depth) of every 1 m cell.</p>
      <p>The whole water area is used if the satellite analysis was run, otherwise only the measured area. Enter the <b>water surface elevation</b> in the project settings for real elevations; otherwise the surface is taken as 0 and elevations appear as negative depths.</p>` } },
  belirsizlik: { grup: "terim", tr: { baslik: "Belirsizlik haritası", metin: `<p>Haritadaki her noktanın derinliği ne kadar güvenilir? Tahmini belirsizlik (1σ):</p>
      <p><code>σ = √( (5 cm + %1·derinlik)² + (eğim × ölçüme uzaklık)² + model² )</code></p>
      <ul><li>İlk terim: tek ışınlı sonarın kendi ölçüm hatası</li><li>İkinci terim: ara değerleme hatası — dip ne kadar eğimli ve en yakın ölçüm ne kadar uzaksa o kadar büyük</li><li>Model: ölçüm hattından 7 m'den uzak, kıyı varsayımıyla doldurulan yerlerde +15 cm</li></ul>
      <p>Uzaklık sınıfları: ölçüldü (≤1 m), ölçüme yakın (1–3 m), ara değer (3–7 m), tahmin (>7 m). Kırmızı / koyu bölgeler yeni ölçüm için en değerli yerlerdir.</p>` },
    en: { baslik: "Uncertainty map", metin: `<p>How reliable is the depth at each point? Estimated uncertainty (1σ):</p>
      <p><code>σ = √( (5 cm + 1%·depth)² + (slope × distance to data)² + model² )</code></p>
      <ul><li>First term: the single-beam sonar's own measurement error</li><li>Second term: interpolation error — larger where the bottom is steep and the nearest measurement far away</li><li>Model: +15 cm more than 7 m from the survey lines, where the shore assumption fills the gap</li></ul>
      <p>Distance classes: measured (≤1 m), near (1–3 m), interpolated (3–7 m), estimate (>7 m). Dark areas are the most valuable places to survey again.</p>` } },
  ses_hizi: { grup: "parametre", tr: { baslik: "Ses hızı düzeltmesi", metin: `<p>Sonar derinliği, sesin gidip dönme süresinden <b>varsayılan bir ses hızıyla</b> hesaplar (çoğu cihazda ~1500 m/s). Tatlı suda gerçek ses hızı sıcaklığa bağlıdır: 5 °C'de ~1427, 15 °C'de ~1466, 25 °C'de ~1497 m/s.</p>
      <ul><li><b>Kapalı</b>: cihazın derinliği olduğu gibi kullanılır.</li><li><b>Su sıcaklığından</b>: kayıttaki sıcaklıktan her ping için gerçek ses hızı hesaplanır (Marczak 1997) ve derinlik oranla düzeltilir.</li><li><b>Elle</b>: CTD / ses hızı ölçeriyle bulduğun değeri gir.</li></ul>
      <p>Etkisi küçüktür ama sistematiktir: 3 m derinlikte 30 m/s fark ≈ 6 cm.</p>` },
    en: { baslik: "Sound speed correction", metin: `<p>The sonar computes depth from the echo travel time using an <b>assumed sound speed</b> (~1500 m/s on most devices). In fresh water the true speed depends on temperature: ~1427 m/s at 5 °C, ~1466 at 15 °C, ~1497 at 25 °C.</p>
      <ul><li><b>Off</b>: device depths are used as they are.</li><li><b>From water temperature</b>: the true speed is computed per ping from the logged temperature (Marczak 1997) and depths are scaled.</li><li><b>Manual</b>: enter a value from a CTD / sound velocity probe.</li></ul>
      <p>Small but systematic: a 30 m/s difference at 3 m depth ≈ 6 cm.</p>` } },
  batma_payi: { grup: "parametre", tr: { baslik: "Batma payı (transducer derinliği)", metin: `<p>Sonar derinliği <b>dönüştürücünün (transducer) yüzünden</b> ölçer. Dönüştürücü su yüzeyinin 10–30 cm altındaysa gerçek su derinliği o kadar fazladır. Buraya dönüştürücünün su yüzeyinden derinliğini metre olarak gir (örn. 0,15).</p>
      <p>Doğrulama analizi, saha ölçümleriyle sabit bir fark bulursa batma payını buna göre önerir.</p>` },
    en: { baslik: "Transducer draft", metin: `<p>The sonar measures depth from the <b>face of the transducer</b>. If the transducer sits 10–30 cm below the surface, the true water depth is that much greater. Enter the transducer depth below the surface in metres (e.g. 0.15).</p>
      <p>If the validation analysis finds a constant offset against field measurements, it suggests a draft accordingly.</p>` } },
  su_kotu: { grup: "parametre", tr: { baslik: "Su yüzeyi kotu", metin: `<p>Tarama günündeki su yüzeyinin kotu (deniz seviyesinden yükseklik ya da yerel bir referansa göre, metre). Bilinmiyorsa 0 bırak; o zaman kotlar "su yüzeyine göre" olur.</p>
      <ul><li><b>Kot–alan–hacim</b> tablosu ve <b>mühendislik çıktılarındaki</b> Z değerleri bu kota göre verilir (kot = su yüzeyi kotu − derinlik).</li>
      <li><b>Değişim analizinde</b> iki tarihin su seviyesi farkını ayırmak için gereklidir.</li></ul>
      <p>Seviye bir eşel (mira) ya da baraj kapağındaki ölçekten okunabilir.</p>` },
    en: { baslik: "Water surface elevation", metin: `<p>Elevation of the water surface on the survey day (above sea level or a local datum, metres). Leave 0 if unknown; elevations are then relative to the water surface.</p>
      <ul><li>The <b>elevation–area–capacity</b> table and Z values in the <b>engineering deliverables</b> use it (elevation = water surface elevation − depth).</li>
      <li>The <b>change analysis</b> needs it to separate water-level differences between dates.</li></ul>
      <p>Read it from a staff gauge or the dam's level gauge.</p>` } },
  kontur: { grup: "parametre", tr: { baslik: "Kontur aralığı", metin: `<p>Eş derinlik çizgilerinin aralığı. <b>Otomatik</b>, derinlik aralığına göre 5–7 çizgi verecek "yuvarlak" bir adım seçer (0,25 / 0,5 / 1 / 2 / 5 m). Sığ göletlerde 0,25 m, derin barajlarda 1–5 m uygundur. Değişiklik analizler yeniden hesaplanınca haritalara ve çıktılara yansır.</p>` },
    en: { baslik: "Contour interval", metin: `<p>Spacing of the depth contours. <b>Automatic</b> picks a round step giving 5–7 lines over the depth range (0.25 / 0.5 / 1 / 2 / 5 m). Use 0.25 m for shallow ponds and 1–5 m for deep reservoirs. Changes appear after the analyses are recomputed.</p>` } },
  koordinat: { grup: "parametre", tr: { baslik: "Koordinat sistemleri", metin: `<ul><li><b>TUREF (ITRF96) / TM 3°</b>: Türkiye'de kamu (DSİ, belediye, tapu) teslimlerinde istenen sistem. Dilim orta meridyeni bölgenin boylamına göre otomatik seçilir (27°, 30°, … 45°).</li>
      <li><b>WGS84 / UTM (6°)</b>: GPS'in doğrudan karşılığı, uluslararası işler için.</li>
      <li><b>ED50 / TM 3° ve ED50 / UTM</b>: eski paftalarla uyum için. Dönüşüm EPSG'deki 7 parametreyle yapılır (birkaç metre doğruluk).</li>
      <li><b>WGS84 enlem / boylam</b>: coğrafi koordinat (DXF bu sistemde üretilmez).</li></ul>` },
    en: { baslik: "Coordinate systems", metin: `<ul><li><b>TUREF (ITRF96) / TM 3°</b>: required for public-sector deliverables in Turkey. The zone's central meridian is chosen automatically (27°, 30°, … 45°).</li>
      <li><b>WGS84 / UTM (6°)</b>: direct GPS equivalent, for international work.</li>
      <li><b>ED50 / TM 3° and ED50 / UTM</b>: for older map sheets. Uses the EPSG 7-parameter transformation (a few metres accuracy).</li>
      <li><b>WGS84 latitude / longitude</b>: geographic coordinates (no DXF in this system).</li></ul>` } },
  duzeltme: { grup: "terim", tr: { baslik: "Dip çizgisini elle düzeltme", metin: `<p>Cihaz bazen dibi yanlış bulur (ikinci yankı, bitki, kabarcık bulutu). <b>Sonar</b> sekmesinde <b>Düzelt</b>'e bas:</p>
      <ul><li><b>Dip çiz</b>: fareyi basılı tutup doğru dip çizgisinin üzerinden sürükle.</li><li><b>Aralık sil</b>: hatalı ping aralığını sürükleyerek işaretle; bu ping'ler haritadan çıkarılır.</li></ul>
      <p>Sarı çizgi şu anki dip, yeşil çizimlerin, kırmızı alanlar silinenler. <b>Kaydet</b>'ten sonra <b>Yeniden hesapla</b> ile haritalar güncellenir. Ctrl+Z geri alır.</p>` },
    en: { baslik: "Editing the bottom line", metin: `<p>The device sometimes picks the bottom wrongly (second echo, vegetation, bubble cloud). In the <b>Sonar</b> tab press <b>Edit</b>:</p>
      <ul><li><b>Draw bottom</b>: hold the mouse button and drag along the correct bottom.</li><li><b>Delete range</b>: drag over a bad ping range; those pings are removed from the map.</li></ul>
      <p>Yellow is the current bottom, green your drawings, red the deleted ranges. After <b>Save</b>, <b>Recompute</b> updates the maps. Ctrl+Z undoes.</p>` } },
  harita_araclari: { grup: "terim", tr: { baslik: "Harita araçları", metin: `<ul><li><b>Mesafe</b> ve <b>alan</b>: noktalara tıkla, çift tık ya da Enter ile bitir.</li>
      <li><b>Profil</b>: hattın noktalarına tıkla; bitince o hat boyunca derinlik kesiti açılır (ölçülen / tahmin ayrı renkte), CSV olarak indirilebilir.</li>
      <li><b>Not</b>: haritaya başlık, açıklama ve renkle işaret koy (iskele, kaya, numune alındı…). Notlar projeye kaydedilir, rapora ve mühendislik çıktılarına eklenir.</li></ul>` },
    en: { baslik: "Map tools", metin: `<ul><li><b>Distance</b> and <b>area</b>: click points, finish with double-click or Enter.</li>
      <li><b>Profile</b>: click points along a line; a depth section along it opens (measured / estimated in different colours) and can be downloaded as CSV.</li>
      <li><b>Note</b>: put a marker with title, description and colour on the map (jetty, rock, sample taken…). Notes are saved with the project and included in the engineering deliverables.</li></ul>` } },
  uc_boyut: { grup: "analiz", tr: { baslik: "3B topografya", metin: `<p><b>3B</b> sekmesi, dip yüzeyini döndürüp yakınlaştırabileceğin üç boyutlu bir model olarak gösterir. Tüm göleti değil, <b>yalnızca istediğin alanı</b> modelleyebilirsin.</p>
      <ol><li><b>Haritadan alan seç</b>'e bas; harita açılır. <b>Dikdörtgen</b> için iki karşıt köşeye tıkla; <b>Çokgen</b> için köşelere tıkla, çift tıkla ya da Enter ile bitir. (Haritadaki küp simgeli araç da aynı işi yapar.)</li>
      <li>Model yalnızca seçtiğin şeklin içinde üretilir; kenarlarında taban plakasına inen bir duvar görünür.</li>
      <li><b>Tüm alan</b> seçimi kaldırır ve ölçülen alanın tamamını gösterir.</li></ol>
      <ul><li><b>Dikey büyütme</b>: göletler yatayda yüzlerce metre, derinlikte birkaç metre olduğundan dip, daha belirgin görünsün diye büyütülür. Ölçüler (hacim, derinlik) etkilenmez.</li>
      <li><b>Renk</b>: derinlik, dip eğimi, zemin sınıfı (zemin analizi yapılmışsa) ya da ölçüm / tahmin ayrımı.</li>
      <li><b>Tahmini alanı dahil et</b>: Uydu analizi yapılmışsa ölçüm hattı dışında kalan yerlerin tahmini derinliği de modele girer; tahmin edilen bölgeler "Ölçüm / tahmin" renginde ayırt edilir.</li>
      <li>Fareyi yüzeyin üzerinde gezdirince o noktanın <b>derinliği</b> ve alan köşesinden uzaklığı görünür.</li>
      <li><b>PNG</b>, <b>OBJ</b> ve <b>STL</b> olarak dışa aktarılır. OBJ / STL taban plakalı kapalı bir katıdır (3B yazıcı, CAD, Blender); ölçüler metredir ve seçili dikey büyütmeyle üretilir (gerçek ölçek için büyütmeyi ×1 yap).</li></ul>` },
    en: { baslik: "3D topography", metin: `<p>The <b>3D</b> tab shows the bottom surface as a three-dimensional model you can rotate and zoom. You can model <b>only the area you want</b>, not the whole pond.</p>
      <ol><li>Press <b>Select area on map</b>; the map opens. For a <b>Rectangle</b> click two opposite corners; for a <b>Polygon</b> click the corners and finish with a double-click or Enter. (The cube tool on the map does the same.)</li>
      <li>The model is built only inside your shape; its edges show a wall down to a base plate.</li>
      <li><b>Whole area</b> clears the selection and shows the whole measured area.</li></ol>
      <ul><li><b>Vertical exaggeration</b>: ponds are hundreds of metres wide but only a few metres deep, so the bottom is stretched vertically to be visible. Measurements (volume, depth) are not affected.</li>
      <li><b>Colour</b>: depth, bottom slope, bottom class (if the bottom analysis was run) or measured / estimated.</li>
      <li><b>Include estimated area</b>: if the satellite analysis was run, the estimated depth beyond the survey lines is included; estimated parts are distinguished in the "Measured / estimated" colour.</li>
      <li>Hover over the surface to read the <b>depth</b> at that point and its distance from the area corner.</li>
      <li>Export as <b>PNG</b>, <b>OBJ</b> or <b>STL</b>. OBJ / STL are closed solids with a base plate (3D printing, CAD, Blender); units are metres and use the selected exaggeration (set it to ×1 for true scale).</li></ul>` } },
  terimler: { grup: "terim", tr: { baslik: "Terimler", metin: `<dl><dt>Ping</dt><dd>Sonarın gönderdiği tek ses atımı ve dönen yankı kaydı (bu cihazda saniyede ~26).</dd>
      <dt>DownVü</dt><dd>Garmin'in aşağı bakan, yüksek frekanslı (≈455/800 kHz) ince ışınlı görüntüleme kanalı.</dd>
      <dt>Genlik</dt><dd>Dönen yankının gücü; görüntüde parlaklık.</dd><dt>Penetrasyon</dt><dd>Sesin yumuşak tortunun içine girip yankının uzaması.</dd>
      <dt>Batimetri</dt><dd>Su altı derinlik haritası.</dd><dt>Kot</dt><dd>Bir referansa (deniz seviyesi) göre yükseklik.</dd>
      <dt>RMSE</dt><dd>Karesel ortalama hata; doğrulamada sonar ile saha ölçümü arasındaki tipik fark.</dd></dl>` },
    en: { baslik: "Glossary", metin: `<dl><dt>Ping</dt><dd>A single sound pulse and its recorded echo (~26 per second on this device).</dd>
      <dt>DownVü</dt><dd>Garmin's down-looking, high-frequency (≈455/800 kHz) narrow-beam imaging channel.</dd>
      <dt>Amplitude</dt><dd>Strength of the returned echo; brightness in the image.</dd><dt>Penetration</dt><dd>Sound entering soft sediment, lengthening the echo.</dd>
      <dt>Bathymetry</dt><dd>Underwater depth map.</dd><dt>Elevation</dt><dd>Height relative to a datum (sea level).</dd>
      <dt>RMSE</dt><dd>Root-mean-square error; the typical difference between sonar and field measurements.</dd></dl>` } },
};
