"""Projede bulunan ciktilardan tek dosyalik HTML rapor uretir (cozumleme/rapor.html).

Hangi analizler calistiysa o bolumler eklenir; gorseller dosyaya gomulur.
"""
import base64
import html
import io
import json
import os

import pandas as pd
from PIL import Image


def oku(yol):
    if not os.path.exists(yol):
        return None
    with open(yol, encoding="utf-8") as f:
        return json.load(f)


def img(yol, alt, no, aciklama):
    if not os.path.exists(yol):
        return ""
    im = Image.open(yol).convert("RGB")
    if im.width > 1600:
        im = im.resize((1600, int(im.height * 1600 / im.width)), Image.LANCZOS)
    b = io.BytesIO()
    im.save(b, "JPEG", quality=85, optimize=True)
    src = "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode()
    return (f'<figure><img src="{src}" alt="{html.escape(alt)}"><figcaption>Şekil {no}. '
            f'{html.escape(aciklama)}</figcaption></figure>')


def sayi(v, n=0):
    if v is None or (isinstance(v, float) and v != v):
        return "–"
    s = f"{v:,.{n}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def tablo(basliklar, satirlar):
    th = "".join(f"<th>{html.escape(b)}</th>" for b in basliklar)
    tr = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in satirlar)
    return f'<div class="tbl"><table><tr>{th}</tr>{tr}</table></div>'


oz = oku("cozumleme/web/ozet.json") or {}
hac = oku("cozumleme/web/hacim.json")
tar = oku("cozumleme/web/taramalar.json")
ad = oku("proje.json") or {}
proje_adi = ad.get("ad", "Sonar kaydı")
sekil = [0]


def S():
    sekil[0] += 1
    return sekil[0]


bol = []
# ---- ozet
kpi = [(f'{sayi(oz.get("derinlik_min"), 2)}–{sayi(oz.get("derinlik_max"), 2)} m', "ölçülen derinlik"),
       (f'{sayi(oz.get("haritalanan_alan_m2"))} m²', "haritalanan alan"),
       (f'{sayi(oz.get("sure_dk"), 0)} dk', "kayıt süresi"),
       (f'{sayi(oz.get("yol_m"))} m', "kat edilen yol")]
if hac:
    kpi[2] = (f'{sayi(hac.get("tum_golet_hacmi_m3_kiyi0m"))}–{sayi(hac.get("tum_golet_hacmi_m3_kiyi0.5m"))} m³', "tahmini toplam hacim")
kpis = "".join(f'<div class="kpi"><b>{a}</b><span>{b}</span></div>' for a, b in kpi)
lead = (f'Kayıt {oz.get("tarih", "")} tarihinde {oz.get("baslangic", "")}–{oz.get("bitis", "")} arasında alındı; '
        f'ölçülen derinlik {sayi(oz.get("derinlik_min"), 2)}–{sayi(oz.get("derinlik_max"), 2)} m '
        f'(ortanca {sayi(oz.get("derinlik_medyan"), 2)} m).')
if hac:
    lead += (f' Su yüzeyi {sayi(hac.get("golet_su_alani_m2"))} m², bunun %{sayi(hac.get("olculen_alan_yuzde"), 1)}\'i ölçüldü; '
             f'tahmini toplam hacim {sayi(hac.get("tum_golet_hacmi_m3_kiyi0m"))}–{sayi(hac.get("tum_golet_hacmi_m3_kiyi0.5m"))} m³.')

bol.append(f'<h2>Kayıt özeti</h2>' + tablo(["Bilgi", "Değer"], [
    ["Tarih ve saat", f'{oz.get("tarih", "")}, {oz.get("baslangic", "")}–{oz.get("bitis", "")}'],
    ["Kayıt süresi", f'{sayi(oz.get("sure_dk"), 1)} dk'],
    ["Ping sayısı", f'{sayi(oz.get("ping"))} (saniyede ~{sayi(oz.get("ping_hz"), 0)})'],
    ["Kanal", html.escape(str(oz.get("kanal", "")))],
    ["Kat edilen yol", f'{sayi(oz.get("yol_m"))} m, ortanca hız {sayi(oz.get("hiz_ort_kmsa"), 1)} km/sa'],
    ["Su sıcaklığı", f'{sayi(oz.get("sicaklik_min"), 1)}–{sayi(oz.get("sicaklik_max"), 1)} °C'],
    ["Elenen ping", f'{sayi(oz.get("elenen_ping"))} (kısa, kopuk derinlik bölümleri)'],
]) + img("cozumleme/uydu/U0_uydu_rota.png", "Rota", S(), "Tekne rotası.")
   + img("cozumleme/grafikler/4_zaman_serileri.png", "Zaman serileri", S(), "Derinlik, hız ve su sıcaklığı."))

bol.append('<h2>Derinlik</h2><p>Ölçülen derinlikler sonar kafasından itibarendir; kafanın batma payı (genelde 10–30 cm) eklenmemiştir.</p>'
           + (img("cozumleme/uydu/U1_uydu_batimetri.png", "Batimetri", S(), "Derinlik haritası (uydu üzerinde).")
              or img("cozumleme/grafikler/5_batimetri_kontur.png", "Batimetri", S(), "Derinlik konturu haritası."))
           + img("cozumleme/grafikler/2_echogram_yakin_plan.png", "Sonar görüntüsü", S(), "Yakın plan sonar görüntüsü."))

if os.path.exists("cozumleme/zemin/zemin_sinif_ozeti.csv"):
    z = pd.read_csv("cozumleme/zemin/zemin_sinif_ozeti.csv")
    bol.append('<h2>Zemin yapısı</h2><p>Sınıflar dip yankısının şeklinden (sertlik, penetrasyon, sönümlenme) elde edilen '
               '<b>göreli</b> sınıflardır ve ~10 m ölçeğinde güvenilirdir; kesin zemin tipi dip numunesiyle doğrulanmalıdır.</p>'
               + tablo(["Sınıf", "Alan", "Ortanca derinlik"],
                       [[html.escape(r["yorum"]), f'%{sayi(r["alan_yuzde"], 1)}', f'{sayi(r["derinlik"], 2)} m'] for _, r in z.iterrows()])
               + (img("cozumleme/uydu/U2_uydu_zemin_numune.png", "Zemin", S(), "Zemin sınıfları ve numune noktaları.")
                  or img("cozumleme/zemin/7_zemin_siniflari.png", "Zemin", S(), "Zemin sınıfları."))
               + img("cozumleme/zemin/6_zemin_oznitelik_haritalari.png", "Öznitelikler", S(), "Akustik zemin ölçüleri."))
if os.path.exists("cozumleme/zemin/numune_noktalari.csv"):
    n = pd.read_csv("cozumleme/zemin/numune_noktalari.csv")
    bol.append('<h2>Numune noktaları</h2><p>Sınıfları doğrulamak için önerilen dip numunesi noktaları '
               '(GPX: <code>cozumleme/zemin/numune_noktalari.gpx</code>).</p>'
               + tablo(["Nokta", "Beklenen zemin", "Enlem", "Boylam", "Derinlik"],
                       [[r["nokta"], html.escape(r["beklenen_zemin"]), f'{r["enlem"]:.6f}', f'{r["boylam"]:.6f}',
                         f'{sayi(r["derinlik_m"], 2)} m'] for _, r in n.iterrows()]))
if hac:
    bol.append('<h2>Hacim, dip şekli ve kapsama</h2>' + tablo(["Büyüklük", "Değer"], [
        ["Su yüzeyi alanı", f'{sayi(hac.get("golet_su_alani_m2"))} m²'],
        ["Ölçülen alan", f'{sayi(hac.get("olculen_alan_m2"))} m² (%{sayi(hac.get("olculen_alan_yuzde"), 1)})'],
        ["Ölçülen alanın hacmi", f'{sayi(hac.get("olculen_alan_hacmi_m3"))} m³'],
        ["Tahmini toplam hacim", f'{sayi(hac.get("tum_golet_hacmi_m3_kiyi0m"))}–{sayi(hac.get("tum_golet_hacmi_m3_kiyi0.5m"))} m³ (kıyıda 0 / 0,5 m varsayımı)'],
        ["Dip eğimi", f'ortanca {sayi(hac.get("egim_medyan_derece"), 1)}°, en dik %5: > {sayi(hac.get("egim_p95_derece"), 1)}°'],
        ["Gerçek ses hızı", f'{sayi(hac.get("gercek_ses_hizi_m_s"), 1)} m/s ({sayi(hac.get("su_sicakligi_C"), 1)} °C tatlı su)'],
        ["Önerilen ikinci tarama", f'{sayi(hac.get("yeni_rota_hat_sayisi"))} hat, ~{sayi(hac.get("yeni_rota_uzunluk_m"))} m, ~{sayi(hac.get("yeni_rota_sure_dk"))} dk'],
    ]) + img("cozumleme/morfoloji/M2_hacim.png", "Hacim", S(), "Tüm su alanı için tahmini derinlik.")
       + img("cozumleme/morfoloji/M3_kapsama_rota.png", "Kapsama", S(), "Kapsama ve önerilen yeni rota.")
       + img("cozumleme/morfoloji/M1_egim_puruzluluk.png", "Eğim", S(), "Dip eğimi ve pürüzlülüğü."))
if tar:
    satir = []
    if "sert_nokta" in tar:
        satir.append(["Kaya, çakıl, batık nesne", f'{tar["sert_nokta"]} aday' if tar["sert_nokta"] else "Bulunmadı"])
    if "bitki_kaplama_ort_yuzde" in tar:
        satir.append(["Su bitkisi örtüsü", f'ortalama kaplama %{sayi(tar["bitki_kaplama_ort_yuzde"], 1)}'])
    if "balik" in tar:
        satir.append(["Balık izi", f'{tar["balik"]}'])
        satir.append(["Gaz kabarcığı izi", f'{tar["kabarcik"]}' if tar["kabarcik"] else "Bulunmadı"])
    bol.append('<h2>Dip ve su kolonu taramaları</h2>' + tablo(["Arama", "Sonuç"], satir)
               + '<p>Vericinin çınlaması nedeniyle yüzeyin ilk ~1,4 m\'si görülemez; balık sayıları göreli ve kalibre değildir.</p>'
               + img("cozumleme/sertnokta/S1_sert_nokta_haritasi.png", "Sert nokta", S(), "Sert nokta / nesne taraması.")
               + img("cozumleme/balik/F3_ornek_kesitler.png", "Balık", S(), "Su kolonu hedeflerinden örnekler.")
               + img("cozumleme/bitki/B2_uydu_bitki_haritasi.png", "Bitki", S(), "Bitki örtüsü tahmini."))

css = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "rapor.css"), encoding="utf-8").read()
out = f"""<!doctype html><html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(proje_adi)} – Sonar Raporu</title><style>{css}</style></head><body><main>
<h1>{html.escape(proje_adi)} – Sonar Analiz Raporu</h1>
<div class="meta">{oz.get("tarih", "")} kaydı · Garmin RSD ({sayi(oz.get("dosya_mb"), 1)} MB) · SonarLab ile üretildi</div>
<p class="lead">{lead}</p><div class="kpis">{kpis}</div>
{"".join(bol)}
<h2>Yöntem</h2><p>RSD dosyası PINGVerter ile çözüldü; analizler SonarLab motoru (Python: numpy, pandas, matplotlib) ile yapıldı.
Uydu altlığı: Esri World Imagery. Zemin ve su kolonu sonuçları kalibre edilmemiş bir balık bulucudan elde edilmiş göreli sonuçlardır.</p>
</main></body></html>"""
with open("cozumleme/rapor.html", "w", encoding="utf-8") as f:
    f.write(out)
print("@@ilerleme 1.0")
print("rapor:", round(len(out) / 1024), "KB")
