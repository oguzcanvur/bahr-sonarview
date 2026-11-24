"""Projedeki ciktilardan tek dosyalik HTML rapor uretir (cozumleme/rapor.html); pdf.py bunu PDF'e cevirir.

Kapak (firma, hazirlayan, imza alani), ozet, hangi analizler calistiysa onlarin bolumleri, ayarlar ve yontem.
Dil ve uzunluk birimi program ayarlarindan gelir (parametreler.json).
"""
import base64
import glob
import html
import io
import json
import os
from datetime import datetime

import pandas as pd
from PIL import Image

from ortak import KOORDINAT_ADLARI, parametreler

P = parametreler()
EN = P.get("dil") == "en"
FT = P.get("birim") == "ft"
KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SOZLUK = {
    "Batimetrik Sonar Analiz Raporu": "Bathymetric Sonar Survey Report",
    "Proje": "Project", "Kayıt tarihi": "Survey date", "Rapor tarihi": "Report date", "Hazırlayan": "Prepared by",
    "Kontrol eden": "Checked by", "Onaylayan": "Approved by", "Ad Soyad": "Name", "Tarih": "Date", "İmza": "Signature",
    "Firma": "Company", "Kayıt": "Recording", "Rapor no": "Report no",
    "ölçülen derinlik": "measured depth", "haritalanan alan": "mapped area", "kayıt süresi": "recording time",
    "kat edilen yol": "distance travelled", "tahmini toplam hacim": "estimated total volume",
    "Özet": "Summary", "Kayıt özeti": "Recording summary", "Bilgi": "Item", "Değer": "Value",
    "Tarih ve saat": "Date and time", "Kayıt süresi": "Recording time", "Ping sayısı": "Ping count", "Kanal": "Channel",
    "Kat edilen yol": "Distance travelled", "Su sıcaklığı": "Water temperature", "Elenen ping": "Rejected pings",
    "Kayıt dosyaları": "Recording files", "Derinlik": "Depth",
    "Tekne rotası.": "Survey track.", "Derinlik, hız ve su sıcaklığı.": "Depth, speed and water temperature.",
    "Derinlik haritası (uydu üzerinde).": "Depth map (on satellite imagery).", "Derinlik konturu haritası.": "Depth contour map.",
    "Yakın plan sonar görüntüsü.": "Close-up sonar image.",
    "Zemin yapısı": "Bottom type", "Sınıf": "Class", "Alan": "Area", "Ortanca derinlik": "Median depth",
    "Zemin sınıfları ve numune noktaları.": "Bottom classes and sampling points.", "Zemin sınıfları.": "Bottom classes.",
    "Akustik zemin ölçüleri.": "Acoustic bottom indicators.",
    "Numune noktaları": "Sampling points", "Nokta": "Point", "Beklenen zemin": "Expected bottom", "Enlem": "Latitude", "Boylam": "Longitude",
    "Hacim, dip şekli ve kapsama": "Volume, bottom shape and coverage", "Büyüklük": "Quantity",
    "Su yüzeyi alanı": "Water surface area", "Ölçülen alan": "Measured area", "Ölçülen alanın hacmi": "Volume of measured area",
    "Tahmini toplam hacim": "Estimated total volume", "Dip eğimi": "Bottom slope", "Gerçek ses hızı": "True sound speed",
    "Önerilen ikinci tarama": "Suggested second survey",
    "Tüm su alanı için tahmini derinlik.": "Estimated depth for the whole water area.",
    "Kapsama ve önerilen yeni rota.": "Coverage and suggested new route.", "Dip eğimi ve pürüzlülüğü.": "Bottom slope and roughness.",
    "Kot – alan – hacim tablosu": "Elevation – area – capacity table", "Kot (m)": "Elevation (m)", "Kot (ft)": "Elevation (ft)",
    "Su derinliği": "Water depth", "Alan (m²)": "Area (m²)", "Hacim (m³)": "Volume (m³)",
    "Kot – alan – hacim eğrisi.": "Elevation – area – capacity curve.",
    "Belirsizlik": "Uncertainty", "Ölçüme uzaklık sınıfları ve tahmini derinlik belirsizliği.": "Distance-to-measurement classes and estimated depth uncertainty.",
    "Saha doğrulaması": "Field validation", "Değişim analizi": "Change analysis",
    "Dip ve su kolonu taramaları": "Bottom and water-column scans", "Arama": "Search", "Sonuç": "Result",
    "Kaya, çakıl, batık nesne": "Rock, gravel, debris", "Su bitkisi örtüsü": "Aquatic vegetation", "Balık izi": "Fish tracks",
    "Gaz kabarcığı izi": "Gas bubble tracks", "Bulunmadı": "Not found", "aday": "candidates",
    "Sert nokta / nesne taraması.": "Hard spot / object scan.", "Su kolonu hedeflerinden örnekler.": "Examples of water-column targets.",
    "Bitki örtüsü tahmini.": "Vegetation estimate.",
    "Mühendislik çıktıları": "Engineering deliverables", "Ayarlar ve düzeltmeler": "Settings and corrections",
    "3B topografya": "3D topography", "3B yüzey görünümü (seçilen alan).": "3D surface view (selected area).",
    "Yöntem": "Method", "Şekil": "Figure", "BAHR SONARVIEW ile üretildi": "Produced with BAHR SONARVIEW",
    "Ses hızı düzeltmesi": "Sound speed correction", "Batma payı": "Transducer draft", "Su yüzeyi kotu": "Water surface elevation",
    "Elle düzeltme": "Manual edits", "Koordinat sistemi": "Coordinate system", "kapalı": "off", "su sıcaklığından": "from water temperature",
    "elle": "manual",
}


def T(s):
    return SOZLUK.get(s, s) if EN else s


def oku(yol):
    if not os.path.exists(yol):
        return None
    with open(yol, encoding="utf-8") as f:
        return json.load(f)


def b64_resim(yol, en=1600, jpeg=True):
    im = Image.open(yol)
    im = im.convert("RGB") if jpeg else im.convert("RGBA")
    if im.width > en:
        im = im.resize((en, int(im.height * en / im.width)), Image.LANCZOS)
    b = io.BytesIO()
    im.save(b, "JPEG" if jpeg else "PNG", quality=85, optimize=True)
    return f"data:image/{'jpeg' if jpeg else 'png'};base64," + base64.b64encode(b.getvalue()).decode()


def sayi(v, n=0):
    if v is None or (isinstance(v, float) and v != v):
        return "–"
    s = f"{v:,.{n}f}"
    return s if EN else s.replace(",", "X").replace(".", ",").replace("X", ".")


def uz(v, n=2):
    """Uzunluk / derinlik: secili birimde."""
    if v is None:
        return "–"
    return f"{sayi(v * 3.28084 if FT else v, n)} {'ft' if FT else 'm'}"


def tablo(basliklar, satirlar, sinif=""):
    th = "".join(f"<th>{html.escape(b)}</th>" for b in basliklar)
    tr = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in satirlar)
    return f'<div class="tbl {sinif}"><table><tr>{th}</tr>{tr}</table></div>'


sekil = [0]


def img(yol, alt, aciklama):
    if not os.path.exists(yol):
        return ""
    sekil[0] += 1
    return (f'<figure><img src="{b64_resim(yol)}" alt="{html.escape(alt)}"><figcaption>{T("Şekil")} {sekil[0]}. '
            f'{html.escape(T(aciklama))}</figcaption></figure>')


oz = oku("cozumleme/web/ozet.json") or {}
hac = oku("cozumleme/web/hacim.json")
tar = oku("cozumleme/web/taramalar.json")
hat = oku("cozumleme/web/hacim_tablosu.json")
dog = oku("cozumleme/web/dogrulama.json")
deg = oku("cozumleme/web/degisim.json")
dis = oku("cozumleme/web/disari.json")
pj = oku("proje.json") or {}
proje_adi = pj.get("ad", "Sonar")
bol = []

# ---------------------------------------------------------------- kapak
logo_yol = os.path.join(KOK, "static", "logo_yatay.png")
logo = f'<img class="marka-logo" alt="BAHR SONARVIEW" src="{b64_resim(logo_yol, 900, jpeg=False)}">' if os.path.exists(logo_yol) else ""
firma_logo = ""
if P.get("firma_logo") and os.path.exists(P["firma_logo"]):
    try:
        firma_logo = f'<img class="firma-logo" alt="" src="{b64_resim(P["firma_logo"], 600, jpeg=False)}">'
    except Exception:
        firma_logo = ""
kayitlar = pj.get("kayitlar") or [{"ad": pj.get("dosya_adi", "")}]
kapak_bilgi = [
    [T("Proje"), html.escape(proje_adi)],
    [T("Kayıt tarihi"), html.escape(f'{oz.get("tarih", "")} {oz.get("baslangic", "")}–{oz.get("bitis", "")}')],
    [T("Kayıt"), html.escape(", ".join(k.get("ad", "") for k in kayitlar))],
    [T("Rapor tarihi"), datetime.now().strftime("%Y-%m-%d")],
]
if P.get("firma_adi"):
    kapak_bilgi.insert(0, [T("Firma"), html.escape(P["firma_adi"])])
if P.get("hazirlayan"):
    kapak_bilgi.append([T("Hazırlayan"), html.escape(P["hazirlayan"])])
imza = "".join(f'<div class="imza"><b>{T(r)}</b><span>{T("Ad Soyad")}: {html.escape(P.get("hazirlayan", "")) if r == "Hazırlayan" else ""}</span>'
               f'<span>{T("Tarih")}:</span><span>{T("İmza")}:</span></div>' for r in ["Hazırlayan", "Kontrol eden", "Onaylayan"])
kapak = f"""<section class="kapak">
<div class="marka-bant">{logo}{firma_logo}</div>
<div class="kapak-orta"><p class="ust-baslik">{T("Batimetrik Sonar Analiz Raporu")}</p><h1>{html.escape(proje_adi)}</h1>
{tablo(["", ""], kapak_bilgi, "kapak-tbl")}</div>
<div class="imzalar">{imza}</div>
<p class="kapak-alt">{T("BAHR SONARVIEW ile üretildi")} · {datetime.now():%Y-%m-%d %H:%M}</p>
</section>"""

# ---------------------------------------------------------------- ozet
kpi = [(f'{uz(oz.get("derinlik_min"))} – {uz(oz.get("derinlik_max"))}', T("ölçülen derinlik")),
       (f'{sayi(oz.get("haritalanan_alan_m2"))} m²', T("haritalanan alan")),
       (f'{sayi(oz.get("sure_dk"), 0)} {"min" if EN else "dk"}', T("kayıt süresi")),
       (f'{sayi(oz.get("yol_m"))} m', T("kat edilen yol"))]
if hac:
    kpi[2] = (f'{sayi(hac.get("tum_golet_hacmi_m3_kiyi0m"))}–{sayi(hac.get("tum_golet_hacmi_m3_kiyi0.5m"))} m³', T("tahmini toplam hacim"))
kpis = "".join(f'<div class="kpi"><b>{a}</b><span>{b}</span></div>' for a, b in kpi)
if EN:
    lead = (f'Recorded on {oz.get("tarih", "")} between {oz.get("baslangic", "")} and {oz.get("bitis", "")}; measured depth '
            f'{uz(oz.get("derinlik_min"))} – {uz(oz.get("derinlik_max"))} (median {uz(oz.get("derinlik_medyan"))}).')
    if hac:
        lead += (f' Water surface {sayi(hac.get("golet_su_alani_m2"))} m², of which {sayi(hac.get("olculen_alan_yuzde"), 1)}% was measured; '
                 f'estimated total volume {sayi(hac.get("tum_golet_hacmi_m3_kiyi0m"))}–{sayi(hac.get("tum_golet_hacmi_m3_kiyi0.5m"))} m³.')
else:
    lead = (f'Kayıt {oz.get("tarih", "")} tarihinde {oz.get("baslangic", "")}–{oz.get("bitis", "")} arasında alındı; '
            f'ölçülen derinlik {uz(oz.get("derinlik_min"))} – {uz(oz.get("derinlik_max"))} (ortanca {uz(oz.get("derinlik_medyan"))}).')
    if hac:
        lead += (f' Su yüzeyi {sayi(hac.get("golet_su_alani_m2"))} m², bunun %{sayi(hac.get("olculen_alan_yuzde"), 1)}\'i ölçüldü; '
                 f'tahmini toplam hacim {sayi(hac.get("tum_golet_hacmi_m3_kiyi0m"))}–{sayi(hac.get("tum_golet_hacmi_m3_kiyi0.5m"))} m³.')

bol.append(f'<h2>{T("Kayıt özeti")}</h2>' + tablo([T("Bilgi"), T("Değer")], [
    [T("Tarih ve saat"), f'{oz.get("tarih", "")}, {oz.get("baslangic", "")}–{oz.get("bitis", "")}'],
    [T("Kayıt dosyaları"), html.escape(", ".join(k.get("ad", "") for k in kayitlar))],
    [T("Kayıt süresi"), f'{sayi(oz.get("sure_dk"), 1)} {"min" if EN else "dk"}'],
    [T("Ping sayısı"), f'{sayi(oz.get("ping"))} (~{sayi(oz.get("ping_hz"), 0)} Hz)'],
    [T("Kanal"), html.escape(str(oz.get("kanal", "")))],
    [T("Kat edilen yol"), f'{sayi(oz.get("yol_m"))} m, {sayi(oz.get("hiz_ort_kmsa"), 1)} km/h'],
    [T("Su sıcaklığı"), f'{sayi(oz.get("sicaklik_min"), 1)}–{sayi(oz.get("sicaklik_max"), 1)} °C'],
    [T("Elenen ping"), f'{sayi(oz.get("elenen_ping"))}'],
]) + img("cozumleme/uydu/U0_uydu_rota.png", "Rota", "Tekne rotası.")
   + img("cozumleme/grafikler/4_zaman_serileri.png", "Zaman serileri", "Derinlik, hız ve su sıcaklığı."))

bp = float(P.get("batma_payi") or 0)
bol.append(f'<h2>{T("Derinlik")}</h2><p>'
           + ((f"Depths are measured from the water surface (transducer draft {uz(bp)} included)." if bp else
               "Depths are measured from the transducer; no transducer draft has been added.") if EN else
              (f"Derinlikler su yüzeyinden itibarendir (batma payı {uz(bp)} eklendi)." if bp else
               "Derinlikler sonar kafasından itibarendir; batma payı eklenmemiştir."))
           + "</p>"
           + (img("cozumleme/uydu/U1_uydu_batimetri.png", "Batimetri", "Derinlik haritası (uydu üzerinde).")
              or img("cozumleme/grafikler/5_batimetri_kontur.png", "Batimetri", "Derinlik konturu haritası."))
           + img("cozumleme/grafikler/2_echogram_yakin_plan.png", "Sonar", "Yakın plan sonar görüntüsü."))

if hat:
    t = pd.DataFrame(hat["tablo"])
    if len(t) > 16:
        t = pd.concat([t.iloc[::max(1, len(t) // 14)], t.iloc[[-1]]]).drop_duplicates()
    sutun = [T("Kot (ft)") if FT else T("Kot (m)"), T("Su derinliği"), T("Alan (m²)"), T("Hacim (m³)")]
    satir = [[sayi(r.kot_m * (3.28084 if FT else 1), 2), uz(r.su_derinligi_m), sayi(r.alan_m2), sayi(r.hacim_m3)] for r in t.itertuples()]
    acik = (f'Computed for the {"whole water area" if "tüm" in hat["kapsam"] else "measured area only"}; water surface elevation {uz(hat["su_kotu"])}. '
            f'Total volume {sayi(hat["toplam_hacim_m3"])} ± {sayi(hat["hacim_belirsizlik_m3"])} m³.') if EN else \
        (f'Hesap kapsamı: {hat["kapsam"]}; su yüzeyi kotu {uz(hat["su_kotu"])}. '
         f'Toplam hacim {sayi(hat["toplam_hacim_m3"])} ± {sayi(hat["hacim_belirsizlik_m3"])} m³ (tahmini).')
    bol.append(f'<h2>{T("Kot – alan – hacim tablosu")}</h2><p>{acik}</p>' + tablo(sutun, satir, "sayisal")
               + img("cozumleme/hacim/K1_kot_alan_hacim.png", "Kot alan hacim", "Kot – alan – hacim eğrisi."))
    sinif = ", ".join(f"{a}: %{sayi(b, 1)}" for a, b in zip(hat["sinif_ad"], hat["sinif_yuzde"]))
    bol.append(f'<h2>{T("Belirsizlik")}</h2><p>'
               + (f'Estimated depth uncertainty (1σ): median ±{sayi(hat["sigma_medyan_cm"], 1)} cm, 90th percentile ±{sayi(hat["sigma_p90_cm"], 1)} cm. '
                  f'It grows with bottom slope and with distance from the survey lines. Distance classes — {html.escape(sinif)}.' if EN else
                  f'Tahmini derinlik belirsizliği (1σ): ortanca ±{sayi(hat["sigma_medyan_cm"], 1)} cm, %90\'lık dilim ±{sayi(hat["sigma_p90_cm"], 1)} cm. '
                  f'Belirsizlik dip eğimi ve ölçüm hattına uzaklıkla artar. Uzaklık sınıfları — {html.escape(sinif)}.')
               + "</p>" + img("cozumleme/hacim/B1_belirsizlik.png", "Belirsizlik", "Ölçüme uzaklık sınıfları ve tahmini derinlik belirsizliği."))

if os.path.exists("cozumleme/zemin/zemin_sinif_ozeti.csv"):
    z = pd.read_csv("cozumleme/zemin/zemin_sinif_ozeti.csv")
    adlar = oku("sinif_adlari.json") or {}
    bol.append(f'<h2>{T("Zemin yapısı")}</h2><p>'
               + ("Classes are <b>relative</b> classes derived from the shape of the bottom echo (hardness, penetration, decay) and are reliable at ~10 m scale; "
                  "the actual bottom type must be confirmed with grab samples." if EN else
                  "Sınıflar dip yankısının şeklinden (sertlik, penetrasyon, sönümlenme) elde edilen <b>göreli</b> sınıflardır ve ~10 m ölçeğinde güvenilirdir; "
                  "kesin zemin tipi dip numunesiyle doğrulanmalıdır.") + "</p>"
               + tablo([T("Sınıf"), T("Alan"), T("Ortanca derinlik")],
                       [[html.escape(adlar.get(str(int(r["sinif"])), r["yorum"])), f'%{sayi(r["alan_yuzde"], 1)}', uz(r["derinlik"])] for _, r in z.iterrows()])
               + (img("cozumleme/uydu/U2_uydu_zemin_numune.png", "Zemin", "Zemin sınıfları ve numune noktaları.")
                  or img("cozumleme/zemin/7_zemin_siniflari.png", "Zemin", "Zemin sınıfları."))
               + img("cozumleme/zemin/6_zemin_oznitelik_haritalari.png", "Öznitelikler", "Akustik zemin ölçüleri."))
if os.path.exists("cozumleme/zemin/numune_noktalari.csv"):
    n = pd.read_csv("cozumleme/zemin/numune_noktalari.csv")
    bol.append(f'<h2>{T("Numune noktaları")}</h2>'
               + tablo([T("Nokta"), T("Beklenen zemin"), T("Enlem"), T("Boylam"), T("Derinlik")],
                       [[r["nokta"], html.escape(r["beklenen_zemin"]), f'{r["enlem"]:.6f}', f'{r["boylam"]:.6f}',
                         uz(r["derinlik_m"])] for _, r in n.iterrows()]))
if hac:
    bol.append(f'<h2>{T("Hacim, dip şekli ve kapsama")}</h2>' + tablo([T("Büyüklük"), T("Değer")], [
        [T("Su yüzeyi alanı"), f'{sayi(hac.get("golet_su_alani_m2"))} m²'],
        [T("Ölçülen alan"), f'{sayi(hac.get("olculen_alan_m2"))} m² (%{sayi(hac.get("olculen_alan_yuzde"), 1)})'],
        [T("Ölçülen alanın hacmi"), f'{sayi(hac.get("olculen_alan_hacmi_m3"))} m³'],
        [T("Tahmini toplam hacim"), f'{sayi(hac.get("tum_golet_hacmi_m3_kiyi0m"))}–{sayi(hac.get("tum_golet_hacmi_m3_kiyi0.5m"))} m³'],
        [T("Dip eğimi"), f'{sayi(hac.get("egim_medyan_derece"), 1)}° (p95 {sayi(hac.get("egim_p95_derece"), 1)}°)'],
        [T("Gerçek ses hızı"), f'{sayi(hac.get("gercek_ses_hizi_m_s"), 1)} m/s ({sayi(hac.get("su_sicakligi_C"), 1)} °C)'],
        [T("Önerilen ikinci tarama"), f'{sayi(hac.get("yeni_rota_hat_sayisi"))} / ~{sayi(hac.get("yeni_rota_uzunluk_m"))} m / ~{sayi(hac.get("yeni_rota_sure_dk"))} {"min" if EN else "dk"}'],
    ]) + img("cozumleme/morfoloji/M2_hacim.png", "Hacim", "Tüm su alanı için tahmini derinlik.")
       + img("cozumleme/morfoloji/M3_kapsama_rota.png", "Kapsama", "Kapsama ve önerilen yeni rota.")
       + img("cozumleme/morfoloji/M1_egim_puruzluluk.png", "Eğim", "Dip eğimi ve pürüzlülüğü."))

if dog:
    satir = []
    dd = dog.get("derinlik") or {}
    if "rmse_m" in dd:
        satir += [["RMSE", f'{sayi(dd["rmse_m"] * 100, 1)} cm'], ["Bias (sonar − saha)" if not EN else "Bias (sonar − field)", f'{sayi(dd["ortalama_fark_m"] * 100, 1)} cm'],
                  ["n", str(dd["kullanilan"])], ["sonar = a·x + b", f'a = {sayi(dd["egim"], 3)}, b = {sayi(dd["kesisim_m"], 3)} m']]
    zz = dog.get("zemin") or {}
    if zz.get("kullanilan"):
        satir.append([("Bottom class agreement" if EN else "Zemin sınıfı uyumu"), f'%{sayi(zz["uyum_yuzde"], 1)} (n = {zz["kullanilan"]})'])
    bol.append(f'<h2>{T("Saha doğrulaması")}</h2>' + (tablo([T("Büyüklük"), T("Değer")], satir) if satir else "")
               + img("cozumleme/dogrulama/D1_derinlik_dogrulama.png", "Doğrulama", "Saha ölçümü ile sonar derinliğinin karşılaştırılması."))
if deg:
    bol.append(f'<h2>{T("Değişim analizi")}</h2>' + tablo([T("Büyüklük"), T("Değer")], [
        ["Taramalar" if not EN else "Surveys", f'{html.escape(deg["eski"]["tarih"])} → {html.escape(deg["yeni"]["tarih"])}' + (f' ({sayi(deg["yil"], 1)} {"yr" if EN else "yıl"})' if deg.get("yil") else "")],
        ["Ortak alan" if not EN else "Common area", f'{sayi(deg["ortak_alan_m2"])} m²'],
        ["Birikim" if not EN else "Deposition", f'{sayi(deg["birikim_m3"])} m³ ({sayi(deg["birikim_alani_m2"])} m²)'],
        ["Oyulma" if not EN else "Erosion", f'{sayi(deg["oyulma_m3"])} m³ ({sayi(deg["oyulma_alani_m2"])} m²)'],
        ["Net", f'{sayi(deg["net_m3"])} m³' + (f' · {sayi(deg["yillik_net_m3"])} m³/{"yr" if EN else "yıl"}' if deg.get("yillik_net_m3") is not None else "")],
    ]) + (f'<p class="note">{"Water levels were assumed equal (no water surface elevation entered)." if EN else "İki projede su yüzeyi kotu girilmediği için su seviyeleri aynı kabul edildi."}</p>' if deg.get("su_seviyesi_uyari") else "")
               + img("cozumleme/degisim/G1_degisim_haritasi.png", "Değişim", "Dip kotu değişimi: kırmızı birikim, mavi oyulma."))
if tar:
    satir = []
    if "sert_nokta" in tar:
        satir.append([T("Kaya, çakıl, batık nesne"), f'{tar["sert_nokta"]} {T("aday")}' if tar["sert_nokta"] else T("Bulunmadı")])
    if "bitki_kaplama_ort_yuzde" in tar:
        satir.append([T("Su bitkisi örtüsü"), f'%{sayi(tar["bitki_kaplama_ort_yuzde"], 1)}'])
    if "balik" in tar:
        satir.append([T("Balık izi"), f'{tar["balik"]}'])
        satir.append([T("Gaz kabarcığı izi"), f'{tar["kabarcik"]}' if tar["kabarcik"] else T("Bulunmadı")])
    bol.append(f'<h2>{T("Dip ve su kolonu taramaları")}</h2>' + tablo([T("Arama"), T("Sonuç")], satir)
               + img("cozumleme/sertnokta/S1_sert_nokta_haritasi.png", "Sert nokta", "Sert nokta / nesne taraması.")
               + img("cozumleme/balik/F3_ornek_kesitler.png", "Balık", "Su kolonu hedeflerinden örnekler.")
               + img("cozumleme/bitki/B2_uydu_bitki_haritasi.png", "Bitki", "Bitki örtüsü tahmini."))
_uc = sorted(glob.glob("cozumleme/3b/*.png"), key=os.path.getmtime)
if _uc:
    bol.append(f'<h2>{T("3B topografya")}</h2>' + img(_uc[-1], "3B topografya", "3B yüzey görünümü (seçilen alan)."))
if dis:
    bol.append(f'<h2>{T("Mühendislik çıktıları")}</h2><p>'
               + (f'{dis["dosya_sayisi"]} files were produced in {html.escape(dis["koordinat"])} (EPSG:{dis["epsg"]}): GeoTIFF, Shapefile, GeoJSON, KML, DXF, XYZ — '
                  f'<code>{html.escape(dis["zip"])}</code>.' if EN else
                  f'{html.escape(dis["koordinat"])} (EPSG:{dis["epsg"]}) koordinat sisteminde {dis["dosya_sayisi"]} dosya üretildi: GeoTIFF, Shapefile, GeoJSON, KML, DXF, XYZ — '
                  f'<code>{html.escape(dis["zip"])}</code>.') + "</p>")

# ---------------------------------------------------------------- ayarlar
mod = {"kapali": T("kapalı"), "sicaklik": T("su sıcaklığından"), "elle": T("elle")}.get(P.get("ses_hizi_modu"), P.get("ses_hizi_modu"))
duz = oku("duzeltmeler.json") or {}
bol.append(f'<h2>{T("Ayarlar ve düzeltmeler")}</h2>' + tablo([T("Bilgi"), T("Değer")], [
    [T("Ses hızı düzeltmesi"), f'{mod}' + (f' ({sayi(P.get("ses_hizi_elle"))} m/s)' if P.get("ses_hizi_modu") == "elle" else "")
     + f' · {"device assumes" if EN else "cihazın varsaydığı"} {sayi(P.get("cihaz_ses_hizi"))} m/s'],
    [T("Batma payı"), uz(bp)],
    [T("Su yüzeyi kotu"), uz(float(P.get("su_kotu") or 0), 3)],
    [T("Elle düzeltme"), f'{len(duz.get("dip", []))} / {len(duz.get("silinen", []))}' + (" (redrawn bottom / deleted ranges)" if EN else " (çizilen dip / silinen aralık)")],
    [T("Koordinat sistemi"), html.escape(KOORDINAT_ADLARI.get(P.get("koordinat"), str(P.get("koordinat"))))],
]))

css = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "rapor.css"), encoding="utf-8").read()
yontem = ("The RSD file(s) were decoded with PINGVerter and analysed with the BAHR SONARVIEW engine (Python: numpy, pandas, matplotlib, pyproj). "
          "Satellite basemap: Esri World Imagery. Bottom and water-column results come from an uncalibrated fish finder and are relative." if EN else
          "RSD dosya(lar)ı PINGVerter ile çözüldü; analizler BAHR SONARVIEW motoru (Python: numpy, pandas, matplotlib, pyproj) ile yapıldı. "
          "Uydu altlığı: Esri World Imagery. Zemin ve su kolonu sonuçları kalibre edilmemiş bir balık bulucudan elde edilmiş göreli sonuçlardır.")
out = f"""<!doctype html><html lang="{'en' if EN else 'tr'}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(proje_adi)} – {T("Batimetrik Sonar Analiz Raporu")}</title><style>{css}</style></head><body><main>
{kapak}
<section class="govde">
<h2 class="ilk">{T("Özet")}</h2>
<p class="lead">{lead}</p><div class="kpis">{kpis}</div>
{"".join(bol)}
<h2>{T("Yöntem")}</h2><p>{yontem}</p>
</section></main></body></html>"""
with open("cozumleme/rapor.html", "w", encoding="utf-8") as f:
    f.write(out)
print("@@ilerleme 1.0")
print("rapor:", round(len(out) / 1024), "KB")
