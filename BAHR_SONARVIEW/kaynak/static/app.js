/* BAHR SONARVIEW arayuzu */
"use strict";

const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const yerel = () => (window.DIL === "en" ? "en-US" : "tr-TR");
const nf = (v, d = 0) => v == null || Number.isNaN(v) ? "–" :
  new Intl.NumberFormat(yerel(), { minimumFractionDigits: d, maximumFractionDigits: d }).format(v);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const FT = 3.28084;
const ftMi = () => D.ayar?.birim === "ft";
const birim = () => (ftMi() ? "ft" : "m");
const uzc = v => v == null ? null : (ftMi() ? v * FT : v);              // uzunluk donusumu
const uz = (v, d = 2) => v == null || Number.isNaN(v) ? "–" : `${nf(uzc(v), d)} ${birim()}`;

const D = {
  projeler: [], pid: null, proje: null, analizTanim: null, ayar: null, ayarMeta: null,
  veri: {}, harita: null, altliklar: {}, katmanlar: {}, acikKatman: new Set(["rota", "batimetri", "kontur", "notlar"]),
  grafikler: [], sonarSatir: 0, oynuyor: false, sekme: "harita", eskiDurum: {}, kesitIstek: 0, isaret: null,
  notlar: [], arac: null, cizim: null, duz: null, duzGecmis: [], duzenle: false, duzKip: "ciz", sonKesit: null, guncel: null,
};

// ------------------------------------------------------------------ yardimcilar
async function api(url, opt = {}) {
  const r = await fetch(url, opt);
  if (!r.ok) {
    let m = r.statusText;
    try { m = (await r.json()).detail || m; } catch { /* yok */ }
    if (typeof m !== "string") m = JSON.stringify(m);
    throw new Error(t(m));
  }
  return r.headers.get("content-type")?.includes("json") ? r.json() : r;
}
const jsonGonder = (url, veri, method = "PUT") => api(url, { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(veri) });
function bildir(m, hata = false) {
  const b = $("#bildirim");
  b.textContent = m; b.className = "bildirim" + (hata ? " hata" : ""); b.hidden = false;
  clearTimeout(bildir.t); bildir.t = setTimeout(() => b.hidden = true, hata ? 7000 : 3500);
}
const purl = (yol) => `/api/projeler/${D.pid}/${yol}`;
const masaustu = () => window.pywebview?.api;
async function yerelKaydet(yol) {
  const r = await masaustu().dosya_kaydet(D.pid, yol);
  if (r?.hata) bildir(t(r.hata), true); else if (r?.kaydedildi) bildir(t("Kaydedildi: ") + r.kaydedildi);
}
function indir(url) { const a = document.createElement("a"); a.href = url; a.download = ""; document.body.append(a); a.click(); a.remove(); }
function raporAc(pdf = true) {
  if (masaustu()) masaustu().rapor_ac(D.pid, pdf);
  else window.open(purl(`dosya/${pdf && D.veri.pdfVar ? "rapor.pdf" : "rapor.html"}`), "_blank", "noopener");
}
function masaustuHazir() {
  if (!masaustu()) return;
  document.body.classList.add("masaustu");
  $("#klasorBtn").hidden = false;
  $(".kenar-alt").innerHTML = `${esc(t("Veriler bu bilgisayarda kalır"))} · <a href="#" id="projeKlasor">${esc(t("Projeler klasörü"))}</a>`;
  $("#projeKlasor").onclick = e => { e.preventDefault(); masaustu().klasor_ac(null); };
}
addEventListener("pywebviewready", masaustuHazir);
const durumAd = () => ({ bekliyor: t("Sırada"), calisiyor: t("Çalışıyor"), bitti: t("Tamamlandı"), hata: t("Hata"), iptal: t("İptal edildi") });
function analizDurum(tur) { return D.proje?.analizler?.[tur]?.durum; }
function sureYaz(dk) { const m = Math.floor(dk), s = Math.round((dk - m) * 60); return `${m}:${String(s).padStart(2, "0")}`; }
const calisiyorMu = () => Object.values(D.proje?.analizler || {}).some(a => a.durum === "bekliyor" || a.durum === "calisiyor");

// ------------------------------------------------------------------ pencere (modal)
function pencereAc({ baslik, govde, alt = "", genis = false, kapaninca = null }) {
  const p = $("#perde");
  $("#pencereBaslik").textContent = baslik;
  $("#pencereGovde").innerHTML = govde;
  $("#pencereAlt").innerHTML = alt;
  $("#pencereAlt").hidden = !alt;
  $(".pencere", p).classList.toggle("genis", genis);
  p.hidden = false;
  dilUygula(p);
  pencereAc.kapaninca = kapaninca;
  return $(".pencere", p);
}
function pencereKapat() { $("#perde").hidden = true; pencereAc.kapaninca?.(); pencereAc.kapaninca = null; }
$("#pencereKapat").onclick = pencereKapat;
$("#perde").addEventListener("mousedown", e => { if (e.target.id === "perde") pencereKapat(); });

// ------------------------------------------------------------------ proje listesi
async function listeYukle() {
  D.projeler = await api("/api/projeler");
  listeCiz();
}
function listeCiz() {
  const el = $("#projeListe"), q = ($("#projeAra").value || "").toLocaleLowerCase(yerel());
  if (!D.projeler.length) { el.innerHTML = `<div class="bos-liste">${esc(t("Henüz proje yok. İlk kaydını yükle."))}</div>`; return; }
  const liste = D.projeler.filter(p => !q || p.ad.toLocaleLowerCase(yerel()).includes(q) || (p.ozet?.tarih || "").includes(q));
  el.innerHTML = liste.map(p => {
    const ds = Object.values(p.analizler || {}).map(a => a.durum);
    const d = ds.some(x => x === "calisiyor" || x === "bekliyor") ? "calisiyor" : ds.includes("hata") ? "hata" : "bitti";
    const oz = p.ozet, nk = (p.kayitlar || []).length;
    const alt = oz ? `${oz.tarih} · ${uz(oz.derinlik_min, 1)}–${uz(oz.derinlik_max, 1)}${nk > 1 ? ` · ${nk} ${t("kayıt")}` : ""}` :
      new Date(p.olusturma * 1000).toLocaleString(yerel());
    return `<button class="proje-oge ${p.id === D.pid ? "aktif" : ""}" data-id="${p.id}">
      <b>${esc(p.ad)}</b><span class="nokta ${d}" title="${durumAd()[d]}"></span><small>${esc(alt)}</small></button>`;
  }).join("") || `<div class="bos-liste">${esc(t("Eşleşen proje yok."))}</div>`;
  $$(".proje-oge", el).forEach(b => b.onclick = () => projeAc(b.dataset.id));
}

// ------------------------------------------------------------------ yukleme
function xhrYukle(url, f, ekAlan, bitti) {
  const fd = new FormData();
  fd.append("dosya", f);
  for (const [k, v] of Object.entries(ekAlan || {})) fd.append(k, v);
  const x = new XMLHttpRequest();
  $("#yuklemeDurum").hidden = false; $("#yuklemeAd").textContent = f.name;
  x.upload.onprogress = e => {
    if (!e.lengthComputable) return;
    const y = e.loaded / e.total * 100;
    $("#yuklemeYuzde").textContent = y < 100 ? `%${nf(y)}` : t("kontrol ediliyor…");
    $("#yuklemeCubuk").style.width = y + "%";
  };
  x.onload = async () => {
    $("#yuklemeDurum").hidden = true;
    if (x.status >= 300) { let m = t("Yükleme başarısız"); try { m = t(JSON.parse(x.responseText).detail); } catch { } bildir(m, true); return; }
    bitti(JSON.parse(x.responseText));
  };
  x.onerror = () => { $("#yuklemeDurum").hidden = true; bildir(t("Yükleme sırasında bağlantı koptu"), true); };
  x.open("POST", url); x.send(fd);
}
function dosyaYukle(f) {
  if (!f) return;
  if (!/\.rsd$/i.test(f.name)) { bildir(t("Yalnızca Garmin .RSD dosyaları destekleniyor"), true); return; }
  xhrYukle("/api/projeler", f, { ad: f.name.replace(/\.rsd$/i, "") }, async p => { await listeYukle(); projeAc(p.id); });
}
async function yerelKayitAc() {
  const p = await masaustu().kayit_ac();
  if (!p) return;
  if (p.hata) { bildir(t(p.hata), true); return; }
  await listeYukle(); projeAc(p.id);
}
async function kayitEkle() {
  if (!D.pid) return;
  if (calisiyorMu()) { bildir(t("Çalışan analiz varken kayıt eklenemez; bitmesini bekleyin ya da iptal edin."), true); return; }
  if (masaustu()) {
    bildir(t("Kayıt ekleniyor…"));
    const r = await masaustu().kayit_ekle(D.pid);
    if (!r) return;
    if (r.hata) { bildir(t(r.hata), true); return; }
    bildir(t("Kayıt eklendi; analizler yeniden hesaplanıyor"));
    durumGuncelle(true);
    return;
  }
  const inp = document.createElement("input");
  inp.type = "file"; inp.accept = ".rsd,.RSD";
  inp.onchange = () => {
    const f = inp.files[0]; if (!f) return;
    xhrYukle(purl("kayitlar"), f, null, () => { bildir(t("Kayıt eklendi; analizler yeniden hesaplanıyor")); durumGuncelle(true); });
  };
  inp.click();
}
function yuklemeBagla() {
  const sec = $("#dosyaSec");
  sec.onchange = () => { dosyaYukle(sec.files[0]); sec.value = ""; };
  for (const el of [$("#yukleKart"), $("#buyukYukle")]) {
    el.onclick = e => { e.preventDefault(); masaustu() ? yerelKayitAc() : sec.click(); };
    el.onkeydown = e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); masaustu() ? yerelKayitAc() : sec.click(); } };
  }
  let say = 0;
  addEventListener("dragenter", e => { if (e.dataTransfer?.types?.includes("Files")) { say++; $("#birak").hidden = false; } });
  addEventListener("dragleave", () => { if (--say <= 0) { say = 0; $("#birak").hidden = true; } });
  addEventListener("dragover", e => e.preventDefault());
  addEventListener("drop", e => { e.preventDefault(); say = 0; $("#birak").hidden = true; dosyaYukle(e.dataTransfer.files[0]); });
}

// ------------------------------------------------------------------ proje acma / durum
async function projeAc(pid) {
  if (D.pid !== pid) {
    katmanlariSifirla(); D.veri = {}; D.eskiDurum = {}; D.sonarSatir = 0; D.oynuyor = false; D.notlar = [];
    duzenleKapat(true); D.grafikHazir = false;
    D.alan3d = null; D.alanKatman = null; if (typeof uc3dSifirla === "function") uc3dSifirla();
  }

  D.pid = pid;
  if (typeof ucAlanYukle === "function" && !D.alan3d) ucAlanYukle();
  history.replaceState(null, "", "#" + pid);
  $("#karsilama").hidden = true; $("#proje").hidden = false;
  $$(".proje-oge").forEach(b => b.classList.toggle("aktif", b.dataset.id === pid));
  await durumGuncelle(true);
}

async function durumGuncelle(ilk = false) {
  if (!D.pid) return;
  let p;
  try { p = await api(`/api/projeler/${D.pid}`); } catch (e) { bildir(e.message, true); return; }
  const onceki = D.eskiDurum;
  D.proje = p;
  const simdi = Object.fromEntries(Object.entries(p.analizler).map(([k, v]) => [k, v.durum]));
  D.eskiDurum = simdi;
  if (ilk || document.activeElement !== $("#projeAd")) $("#projeAd").value = p.ad;
  ustBilgi();
  const temel = p.analizler.temel || {};
  const temelHazir = temel.durum === "bitti" || (D.veri.ozet && temel.durum !== "hata" && temel.durum !== "iptal" && onceki.temel === "bitti");
  $("#isleniyor").hidden = temel.durum === "bitti" || temel.durum === "hata" || temel.durum === "iptal" || (!!D.veri.ozet);
  $("#hataKutu").hidden = !(temel.durum === "hata" || temel.durum === "iptal") || !!D.veri.ozet;
  if (temel.durum === "hata") $("#hataKutu").innerHTML = `<b>${esc(t("Analiz tamamlanamadı."))}</b> ${esc(t(temel.mesaj || ""))}
    <div class="hk-alt"><button class="btn kucuk" data-calistir="temel">${esc(t("Tekrar dene"))}</button><button class="btn hayalet kucuk" data-hata-raporu>${esc(t("Hata raporu oluştur"))}</button></div>`;
  if (temel.durum === "iptal") $("#hataKutu").innerHTML = `<b>${esc(t("Analiz iptal edildi."))}</b>
    <div class="hk-alt"><button class="btn kucuk" data-calistir="temel">${esc(t("Yeniden başlat"))}</button></div>`;
  $$("#hataKutu [data-calistir]").forEach(b => b.onclick = () => analizBaslat(b.dataset.calistir));
  $$("#hataKutu [data-hata-raporu]").forEach(b => b.onclick = hataRaporu);
  if (temel.durum !== "bitti" && !D.veri.ozet) isleniyorCiz(temel);
  $("#sekmeler").hidden = !(temel.durum === "bitti" || D.veri.ozet);
  $("#guncelDegil").hidden = !(p.guncel_degil && temelHazir && !calisiyorMu());
  if (temel.durum === "bitti") {
    if (ilk || onceki.temel !== "bitti") {
      try { await temelYukle(); } catch (e) { bildir(t("Harita verisi yüklenemedi: ") + e.message, true); }
      for (const tur of ["zemin", "uydu", "taramalar", "dogrulama", "degisim", "disari", "rapor"]) if (simdi[tur] === "bitti") await ekVeriYukle(tur);
      if (D.harita) katmanlariYenile();
      if (ilk) sekmeAc(D.sekme);
      if (!ilk && onceki.temel) bildir(t("Temel analiz tamamlandı"));
    }
    for (const [tur, d] of Object.entries(simdi)) {
      if (tur === "temel") continue;
      if (d === "bitti" && onceki[tur] && onceki[tur] !== "bitti") {
        bildir(`${t(D.analizTanim?.[tur]?.ad || tur)} ${t("tamamlandı")}`);
        await ekVeriYukle(tur);
        if (D.harita) katmanlariYenile(tur);
        if (D.sekme === "dosya") dosyalarCiz();
      }
      if (d === "hata" && onceki[tur] && onceki[tur] !== "hata") bildir(`${t(D.analizTanim?.[tur]?.ad || tur)}: ${t(p.analizler[tur].mesaj || "hata")}`, true);
    }
  }
  analizKartlariCiz();
  const calisan = calisiyorMu();
  $("#analizRozet").hidden = !calisan; $("#analizRozet").textContent = "●";
  clearTimeout(durumGuncelle.t);
  if (calisan) durumGuncelle.t = setTimeout(() => durumGuncelle(), 1500);
  if (ilk || JSON.stringify(onceki) !== JSON.stringify(simdi)) listeYukle();
}

function isleniyorCiz(a) {
  const adimlar = D.analizTanim?.temel?.adimlar || [];
  const y = (a.ilerleme || 0) * 100;
  $("#isleniyorCubuk").style.width = Math.max(3, y) + "%";
  $("#isleniyorAdim").textContent = a.durum === "bekliyor" ? `${t("Sırada bekliyor")}${D.proje.kuyruk ? ` (${D.proje.kuyruk} ${t("iş önde")})` : ""}…` :
    `${t(a.adim || "Hazırlanıyor")} · %${nf(y)}`;
  const i = adimlar.indexOf(a.adim);
  $("#isleniyorAdimlar").innerHTML = adimlar.map((s, j) => `<li class="${j < i ? "tamam" : j === i ? "su-an" : ""}">${esc(t(s))}</li>`).join("");
}

function ustBilgi() {
  const oz = D.veri.ozet || D.proje.ozet;
  const p = D.proje, nk = (p.kayitlar || []).length;
  const cip = [];
  if (oz) cip.push(`${oz.tarih} · ${oz.baslangic}–${oz.bitis}`, `${nf(oz.ping)} ping`, oz.kanal.split(" (")[0]);
  cip.push(nk > 1 ? `${nk} ${t("kayıt")} · ${nf(p.boyut / 1e6, 0)} MB` : `${p.kayitlar?.[0]?.ad || p.dosya_adi} · ${nf(p.boyut / 1e6, 1)} MB`);
  const ep = p.etkin_parametreler || {};
  if (+ep.batma_payi) cip.push(`${t("batma payı")} ${uz(+ep.batma_payi)}`);
  if (ep.ses_hizi_modu && ep.ses_hizi_modu !== "kapali") cip.push(t("ses hızı düzeltmeli"));
  $("#projeMeta").innerHTML = cip.map(c => `<span class="cip">${esc(c)}</span>`).join("");
  const k = $("#kpiler");
  if (!oz) { k.innerHTML = ""; return; }
  const h = D.veri.hacim, ht = D.veri.hacimTablo;
  const kpi = [
    [t("Derinlik"), `${nf(uzc(oz.derinlik_min), 1)}–${nf(uzc(oz.derinlik_max), 1)}`, birim()],
    [t("Ortanca derinlik"), nf(uzc(oz.derinlik_medyan), 2), birim()],
    [t("Haritalanan alan"), nf(oz.haritalanan_alan_m2), "m²"],
    h ? [t("Tahmini hacim"), `${nf(h.tum_golet_hacmi_m3_kiyi0m / 1000, 1)}–${nf(h["tum_golet_hacmi_m3_kiyi0.5m"] / 1000, 1)}`, t("bin m³")] :
      ht ? [t("Ölçülen hacim"), nf(ht.toplam_hacim_m3), "m³"] : [t("Kat edilen yol"), nf(oz.yol_m), "m"],
    [t("Kayıt süresi"), nf(oz.sure_dk), t("dk")],
    ht ? [t("Belirsizlik (ortanca)"), `±${nf(ht.sigma_medyan_cm, 0)}`, "cm"] : [t("Su sıcaklığı"), `${nf(oz.sicaklik_min, 1)}–${nf(oz.sicaklik_max, 1)}`, "°C"],
  ];
  k.innerHTML = kpi.map(([a, b, c]) => `<div class="kpi"><span>${esc(a)}</span><b>${b}</b><small>${esc(c)}</small></div>`).join("");
}

// ------------------------------------------------------------------ veri yukleme
async function webJson(ad) {
  const r = await fetch(purl("web/" + ad) + "?t=" + Date.now());
  if (!r.ok) throw new Error(`${ad} alınamadı`);
  return r.json();
}
const istegeBagli = async ad => { try { return await webJson(ad); } catch { return null; } };

async function temelYukle() {
  const [ozet, rota, zaman, kb, kontur] = await Promise.all(["ozet.json", "rota.json", "zaman.json", "katman_batimetri.json", "kontur.geojson"].map(webJson));
  const renk = (await istegeBagli("renk.json")) || (await webJson("renk_viridis_r.json"));
  Object.assign(D.veri, { ozet, rota, zaman, kb, kontur, renk });
  D.veri.kbel = await istegeBagli("katman_belirsizlik.json");
  D.veri.hacimTablo = await istegeBagli("hacim_tablosu.json");
  try { D.notlar = await api(purl("notlar")); } catch { D.notlar = []; }
  ustBilgi();
  haritaKur();
  katmanlariKur();
  $("#zamanCubuk").max = ozet.toplam_satir - 1;
  $("#zcSon").textContent = `${nf(ozet.sure_dk, 1)} ${t("dk")}`;
  if (!D.sonarSatir || D.sonarSatir >= ozet.toplam_satir) D.sonarSatir = rota.satir[Math.floor(rota.satir.length / 2)];
  D.grafikHazir = false;
  if (D.sekme === "grafik") grafikKur();
  if (D.sekme === "sonar") sonarKur();
}

async function ekVeriYukle(tur) {
  try {
    if (tur === "zemin") {
      const [kz, ks, kp, num] = await Promise.all(["katman_zemin.json", "katman_sertlik.json", "katman_penetrasyon.json", "numune.geojson"].map(webJson));
      Object.assign(D.veri, { kz, ks, kp, num });
      D.acikKatman.add("numune");
    } else if (tur === "uydu") {
      const [hacim, ktg, yr] = await Promise.all(["hacim.json", "katman_tum_golet.json", "yeni_rota.json"].map(webJson));
      Object.assign(D.veri, { hacim, ktg, yr });
      D.veri.kiyi = await istegeBagli("kiyi.json");
      D.veri.kbel = await istegeBagli("katman_belirsizlik.json");
      D.veri.hacimTablo = await istegeBagli("hacim_tablosu.json");
      D.grafikHazir = false;
      ustBilgi();
    } else if (tur === "taramalar") {
      D.veri.tar = await webJson("taramalar.json");
      D.veri.balik = await istegeBagli("balik.geojson");
      D.veri.sert = await istegeBagli("sertnokta.geojson");
    } else if (tur === "degisim") {
      D.veri.degisim = await istegeBagli("degisim.json");
      D.veri.kdeg = await istegeBagli("katman_degisim.json");
      if (D.veri.kdeg) D.acikKatman.add("degisim");
    } else if (tur === "dogrulama") {
      D.veri.dogrulama = await istegeBagli("dogrulama.json");
    } else if (tur === "disari") {
      D.veri.disari = await istegeBagli("disari.json");
    } else if (tur === "rapor") {
      D.veri.pdfVar = (await fetch(purl("dosya/rapor.pdf"), { method: "HEAD" })).ok;
    }
  } catch (e) { console.warn(tur, e); }
}

// ------------------------------------------------------------------ harita
function haritaKur() {
  if (D.harita) { D.harita.invalidateSize(); return; }
  const m = L.map("harita", { zoomControl: true, preferCanvas: true, maxZoom: 22, attributionControl: true });
  D.harita = m;
  D.altliklar = {
    uydu: L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
      { maxNativeZoom: 19, maxZoom: 22, attribution: "Esri, Maxar, Earthstar Geographics" }),
    koyu: L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
      { maxNativeZoom: 20, maxZoom: 22, attribution: "© OpenStreetMap, © CARTO" }),
  };
  D.altliklar.uydu.addTo(m);
  L.control.scale({ imperial: ftMi(), metric: !ftMi(), position: "bottomright" }).addTo(m);
  $$("#altlikSec button").forEach(b => b.onclick = () => {
    $$("#altlikSec button").forEach(x => x.classList.toggle("aktif", x === b));
    Object.values(D.altliklar).forEach(l => m.removeLayer(l));
    if (D.altliklar[b.dataset.a]) D.altliklar[b.dataset.a].addTo(m);
  });
  m.on("click", e => (D.arac ? aracTik(e.latlng) : haritaTik(e.latlng)));
  m.on("dblclick", e => { if (D.arac) { L.DomEvent.stop(e); aracBitir(); } });
  m.on("mousemove", e => { if (D.arac && D.cizim) cizimOnizle(e.latlng); });
  m.once("click", () => $("#haritaIpucu").style.opacity = 0);
  if ($("#harita").clientWidth > 50) { m.fitBounds(D.veri.ozet.sinir, { padding: [40, 40] }); }
  alanKatmaniCiz();
}

const KATMANLAR = [
  { id: "rota", ad: "Tekne rotası", gerekir: "temel", yap: rotaKatmani, efsane: "derinlik" },
  { id: "batimetri", ad: "Derinlik haritası", gerekir: "temel", yap: () => resimKatmani(D.veri.kb), efsane: "derinlik" },
  { id: "kontur", ad: "Eş derinlik çizgileri", gerekir: "temel", yap: konturKatmani },
  { id: "belirsizlik", ad: "Belirsizlik", gerekir: "temel", veri: "kbel", yap: () => resimKatmani(D.veri.kbel), efsane: "belirsizlik" },
  { id: "tum_golet", ad: "Tüm su alanı (tahmin)", gerekir: "uydu", veri: "ktg", yap: () => resimKatmani(D.veri.ktg), efsane: "tum" },
  { id: "kiyi", ad: "Kıyı çizgisi", gerekir: "uydu", veri: "kiyi", yap: kiyiKatmani },
  { id: "yeni_rota", ad: "Önerilen yeni rota", gerekir: "uydu", veri: "yr", yap: yeniRotaKatmani },
  { id: "zemin", ad: "Zemin sınıfları", gerekir: "zemin", veri: "kz", yap: () => resimKatmani(D.veri.kz), efsane: "zemin" },
  { id: "sertlik", ad: "Dip sertliği", gerekir: "zemin", veri: "ks", yap: () => resimKatmani(D.veri.ks), efsane: "sertlik" },
  { id: "penetrasyon", ad: "Penetrasyon", gerekir: "zemin", veri: "kp", yap: () => resimKatmani(D.veri.kp), efsane: "penetrasyon" },
  { id: "numune", ad: "Numune noktaları", gerekir: "zemin", veri: "num", yap: numuneKatmani },
  { id: "degisim", ad: "Dip değişimi", gerekir: "degisim", veri: "kdeg", yap: () => resimKatmani(D.veri.kdeg), efsane: "degisim" },
  { id: "balik", ad: "Balık izleri", gerekir: "taramalar", veri: "balik", yap: balikKatmani },
  { id: "sert", ad: "Sert nokta / nesne", gerekir: "taramalar", veri: "sert", yap: sertKatmani },
  { id: "notlar", ad: "Notlar ve işaretler", gerekir: "temel", yap: notKatmani },
];
const SIRA = ["tum_golet", "batimetri", "belirsizlik", "zemin", "sertlik", "penetrasyon", "degisim", "kontur", "kiyi", "rota", "yeni_rota", "numune", "balik", "sert", "notlar"];

function katmanlariSifirla() {
  for (const l of Object.values(D.katmanlar)) D.harita?.removeLayer(l);
  D.katmanlar = {};
  D.acikKatman = new Set(["rota", "batimetri", "kontur", "notlar"]);
  aracKapat();
  if (D.harita) { D.harita.remove(); D.harita = null; }
  D.haritaSigdi = false;
  D.isaret = null; D.alanKatman = null;
  $("#kesitCekmece").hidden = true; $("#profilCekmece").hidden = true;
}
function katmanlariYenile() {
  for (const l of Object.values(D.katmanlar)) D.harita?.removeLayer(l);
  D.katmanlar = {};
  katmanlariKur();
}
function katmanVar(k) { return analizDurum(k.gerekir) === "bitti" && (!k.veri || D.veri[k.veri]); }
function katmanlariKur() {
  const liste = $("#katmanListe");
  liste.innerHTML = "";
  for (const k of KATMANLAR) {
    const var_ = katmanVar(k);
    if (!var_ && ["belirsizlik", "degisim"].includes(k.id) && analizDurum(k.gerekir) !== "bitti") continue;
    const sayi = k.id === "numune" && D.veri.num ? D.veri.num.features.length :
      k.id === "balik" && D.veri.balik ? D.veri.balik.features.length :
      k.id === "sert" && D.veri.sert ? D.veri.sert.features.length :
      k.id === "notlar" ? D.notlar.length : null;
    const el = document.createElement("label");
    el.className = "katman" + (var_ ? "" : " kilitli");
    el.title = var_ ? "" : `${t(D.analizTanim?.[k.gerekir]?.ad || k.gerekir)} ${t("çalıştırılınca açılır")}`;
    el.innerHTML = `<input type="checkbox" ${var_ && D.acikKatman.has(k.id) ? "checked" : ""} ${var_ ? "" : "disabled"}><span class="anahtar"></span>${esc(t(k.ad))}${sayi != null ? `<small>${sayi}</small>` : ""}${!var_ ? `<small>${esc(t("kilitli"))}</small>` : ""}`;
    $("input", el).onchange = e => { e.target.checked ? D.acikKatman.add(k.id) : D.acikKatman.delete(k.id); katmanUygula(); };
    liste.append(el);
  }
  katmanUygula();
}
function katmanUygula() {
  if (!D.harita) return;
  for (const id of SIRA) {
    const k = KATMANLAR.find(x => x.id === id);
    const ac = katmanVar(k) && D.acikKatman.has(id);
    if (ac && !D.katmanlar[id]) { try { D.katmanlar[id] = k.yap(); } catch (e) { console.warn(id, e); continue; } }
    if (D.katmanlar[id]) { D.harita.removeLayer(D.katmanlar[id]); if (ac) D.katmanlar[id].addTo(D.harita); }
  }
  if (D.isaret) D.isaret.bringToFront?.();
  if (D.cizim?.grup) D.cizim.grup.eachLayer(l => l.bringToFront?.());
  efsaneCiz();
}
function resimKatmani(k) { return L.imageOverlay(purl("web/" + k.png) + "?t=" + Date.now(), k.sinir, { opacity: 1, interactive: false }); }

function rotaKatmani() {
  const { lat, lon, dep } = D.veri.rota, { min, max } = D.veri.kb;
  const g = L.layerGroup(), ren = L.canvas({ padding: 0.3 });
  let bas = 0;
  const kova = i => dep[i] == null ? -1 : Math.round(Math.max(0, Math.min(1, (dep[i] - min) / (max - min))) * 10);
  for (let i = 1; i <= lat.length; i++) {
    if (i === lat.length || kova(i) !== kova(bas)) {
      const pts = []; for (let j = bas; j <= Math.min(i, lat.length - 1); j++) pts.push([lat[j], lon[j]]);
      const c = kova(bas) < 0 ? "#94a3b8" : D.veri.renk[kova(bas)];
      L.polyline(pts, { color: c, weight: 3, opacity: kova(bas) < 0 ? 0.45 : 0.95, renderer: ren, interactive: false }).addTo(g);
      bas = i;
    }
  }
  return g;
}
function konturKatmani() {
  return L.geoJSON(D.veri.kontur, {
    style: { color: "#ffffff", weight: 1.1, opacity: 0.75 },
    onEachFeature: (f, l) => l.bindTooltip(uz(f.properties.derinlik, 2), { sticky: true }),
  });
}
function kiyiKatmani() {
  const { lat, lon } = D.veri.kiyi, g = L.layerGroup(), ren = L.canvas();
  for (let i = 0; i < lat.length; i += 2) L.circleMarker([lat[i], lon[i]], { radius: 1.2, color: "#fff", weight: 0, fillOpacity: .8, renderer: ren, interactive: false }).addTo(g);
  return g;
}
function yeniRotaKatmani() {
  const { lat, lon, hat } = D.veri.yr, g = L.layerGroup();
  L.polyline(lat.map((a, i) => [a, lon[i]]), { color: "#facc15", weight: 2.5, dashArray: "6 6", interactive: false }).addTo(g);
  let son = -1;
  lat.forEach((a, i) => {
    if (hat[i] === son) return; son = hat[i];
    L.marker([a, lon[i]], { icon: L.divIcon({ className: "", html: `<div class="hat-no">${hat[i]}</div>`, iconSize: [20, 20] }) })
      .bindTooltip(i === 0 ? t("Başlangıç — hat 1") : `${t("Hat")} ${hat[i]}`).addTo(g);
  });
  return g;
}
function numuneKatmani() {
  return L.geoJSON(D.veri.num, {
    pointToLayer: (f, ll) => L.marker(ll, { icon: L.divIcon({ className: "", iconSize: [26, 26], html: `<div class="numune-ikon">★</div>` }) }),
    onEachFeature: (f, l) => l.bindPopup(`<b>${esc(f.properties.nokta)}</b><br>${esc(f.properties.beklenen_zemin)}<br>${t("Derinlik")} ${uz(f.properties.derinlik_m, 2)}<br><small>${f.geometry.coordinates[1].toFixed(6)}, ${f.geometry.coordinates[0].toFixed(6)}</small>`),
  });
}
function balikKatmani() {
  return L.geoJSON(D.veri.balik, {
    pointToLayer: (f, ll) => L.circleMarker(ll, { radius: 6, color: "#111", weight: 1, fillColor: f.properties.tur === "balik" ? "#fb923c" : "#22d3ee", fillOpacity: .95 }),
    onEachFeature: (f, l) => l.bindTooltip(`${f.properties.tur === "balik" ? t("Balık izi") : t("Gaz kabarcığı")} · ${uz(f.properties.derinlik, 2)} · ${nf(f.properties.dk, 1)}. ${t("dk")}`),
  });
}
function sertKatmani() {
  return L.geoJSON(D.veri.sert, {
    pointToLayer: (f, ll) => L.circleMarker(ll, { radius: 9, color: "#f43f5e", weight: 3, fill: false }),
    onEachFeature: (f, l) => l.bindTooltip(`${esc(f.properties.no)}: ${esc(f.properties.tur)} · ${uz(f.properties.derinlik, 2)}`),
  });
}
function notKatmani() {
  const g = L.layerGroup();
  for (const n of D.notlar) {
    const m = L.marker([n.lat, n.lon], { icon: L.divIcon({ className: "", iconSize: [28, 36], iconAnchor: [14, 34], html: `<div class="not-ikon" style="--renk:${esc(n.renk || "#f59e0b")}"></div>` }) });
    m.bindPopup(() => {
      const el = document.createElement("div");
      el.className = "not-popup";
      el.innerHTML = `<b>${esc(n.baslik || t("Not"))}</b>${n.metin ? `<p>${esc(n.metin)}</p>` : ""}<small>${n.lat.toFixed(6)}, ${n.lon.toFixed(6)} · ${esc((n.tarih || "").replace("T", " "))}</small>
        <div class="np-alt"><button class="btn hayalet kucuk" data-n="duzenle">${esc(t("Düzenle"))}</button><button class="btn hayalet kucuk tehlike" data-n="sil">${esc(t("Sil"))}</button></div>`;
      $("[data-n=duzenle]", el).onclick = () => { D.harita.closePopup(); notPenceresi(n); };
      $("[data-n=sil]", el).onclick = async () => { D.harita.closePopup(); D.notlar = D.notlar.filter(x => x.id !== n.id); await notlariKaydet(); };
      return el;
    });
    m.addTo(g);
  }
  return g;
}

function efsaneCiz() {
  const e = $("#efsane");
  const acik = id => D.acikKatman.has(id) && D.katmanlar[id] && D.harita.hasLayer(D.katmanlar[id]);
  const grad = D.veri.renk ? `linear-gradient(90deg, ${D.veri.renk.join(",")})` : "";
  let h = "";
  if (acik("degisim") && D.veri.kdeg) h = `<b>${t("Dip kotu değişimi")}</b><div class="skala" style="background:linear-gradient(90deg,#2166ac,#f7f7f7,#b2182b)"></div><div class="skala-et"><span>${uz(D.veri.kdeg.min, 2)}</span><span>0</span><span>+${uz(D.veri.kdeg.max, 2)}</span></div><div class="skala-et"><span>← ${t("oyulma")}</span><span>${t("birikim")} →</span></div>`;
  else if (acik("zemin") && D.veri.kz) h = `<b>${t("Zemin sınıfları")} <span class="ince">(${t("göreli")})</span></b>` + D.veri.kz.siniflar.map(s => `<div class="sinif"><i style="background:${s.renk}"></i>${esc(s.ad)} <span class="ince">%${nf(s.alan_yuzde)}</span></div>`).join("");
  else if (acik("belirsizlik") && D.veri.kbel) h = `<b>${t("Tahmini belirsizlik")} (± cm)</b><div class="skala" style="background:linear-gradient(90deg,#fcfdbf,#fc8961,#b73779,#51127c,#000004)"></div><div class="skala-et"><span>0</span><span>${nf(D.veri.kbel.max)}</span></div>`;
  else if (acik("sertlik")) h = `<b>${t("Dip sertliği")}</b><div class="skala" style="background:linear-gradient(90deg,#ffffe5,#fe9929,#662506)"></div><div class="skala-et"><span>${t("yumuşak")}</span><span>${t("sert")}</span></div>`;
  else if (acik("penetrasyon")) h = `<b>${t("Penetrasyon")}</b><div class="skala" style="background:linear-gradient(90deg,#fff7fb,#74a9cf,#023858)"></div><div class="skala-et"><span>${t("yüzeyden seker")}</span><span>${t("tortuya girer")}</span></div>`;
  else if (acik("tum_golet") && D.veri.ktg) h = `<b>${t("Tahmini derinlik")} (${birim()})</b><div class="skala" style="background:${grad}"></div><div class="skala-et"><span>0</span><span>${nf(uzc(D.veri.ktg.max), 1)}</span></div>`;
  else if ((acik("batimetri") || acik("rota")) && D.veri.kb) h = `<b>${t("Derinlik")} (${birim()})</b><div class="skala" style="background:${grad}"></div><div class="skala-et"><span>${nf(uzc(D.veri.kb.min), 1)}</span><span>${nf(uzc(D.veri.kb.max), 1)}</span></div>`;
  e.innerHTML = h; e.hidden = !h;
}

// ---- haritada tiklama -> en yakin rota noktasi -> kesit
function enYakinRota(ll) {
  const { lat, lon } = D.veri.rota;
  const p = D.harita.latLngToContainerPoint(ll);
  let en = -1, ed = 1e9;
  for (let i = 0; i < lat.length; i++) {
    const q = D.harita.latLngToContainerPoint([lat[i], lon[i]]);
    const d = (q.x - p.x) ** 2 + (q.y - p.y) ** 2;
    if (d < ed) { ed = d; en = i; }
  }
  return ed <= 30 * 30 ? en : -1;
}
function isaretKoy(i) {
  const { lat, lon } = D.veri.rota;
  if (!D.isaret) D.isaret = L.circleMarker([lat[i], lon[i]], { radius: 8, color: "#fff", weight: 3, fillColor: "#22d3ee", fillOpacity: 1 }).addTo(D.harita);
  else D.isaret.setLatLng([lat[i], lon[i]]).addTo(D.harita);
}
async function haritaTik(ll) {
  const i = enYakinRota(ll);
  if (i < 0) return;
  isaretKoy(i);
  const r = D.veri.rota;
  D.sonarSatir = r.satir[i];
  $("#profilCekmece").hidden = true;
  $("#kesitCekmece").hidden = false;
  $("#kcBilgi").textContent = `${sureYaz(r.t[i] / 60)}. ${t("dk")} · ${t("derinlik")} ${uz(r.dep[i], 2)} · ${r.lat[i].toFixed(6)}, ${r.lon[i].toFixed(6)}`;
  await kesitGetir(r.satir[i], 600, "bakir", $("#kcImg"), $("#kcCanvas"));
}

// ------------------------------------------------------------------ harita araclari
const ARAC_IPUCU = {
  mesafe: "Tıklayarak noktalar ekle · çift tık ya da Enter: bitir · Esc: iptal",
  alan: "Alanın köşelerine tıkla · çift tık ya da Enter: bitir · Esc: iptal",
  profil: "Profil hattının noktalarına tıkla · çift tık ya da Enter: profili çiz",
  not: "Not eklemek istediğin yere tıkla",
  alan3d_dikdortgen: "3B alan: dikdörtgenin iki karşıt köşesine tıkla · Esc: iptal",
  alan3d_cokgen: "3B alan: alanın köşelerine tıkla · çift tık ya da Enter: bitir · Esc: iptal",
};
function aracSec(a) {
  if (a === "temizle") { cizimleriTemizle(); return; }
  if (D.arac === a) { aracKapat(); return; }
  aracKapat();
  D.arac = a;
  $$("#aracCubugu button").forEach(b => b.classList.toggle("aktif", b.dataset.arac === a));
  $("#aracIpucu").textContent = t(ARAC_IPUCU[a === "alan3d" ? `alan3d_${UC.kip}` : a]); $("#aracIpucu").hidden = false;
  D.harita.doubleClickZoom.disable();
  $("#harita").classList.add("cizim-kipi");
  if (a !== "not") D.cizim = { noktalar: [], grup: D.cizim?.grup || L.layerGroup().addTo(D.harita), gecici: null };
}
function aracKapat() {
  if (D.cizim?.gecici) D.cizim.grup.removeLayer(D.cizim.gecici);
  D.arac = null;
  if (D.cizim) D.cizim = { noktalar: [], grup: D.cizim.grup, gecici: null };
  $$("#aracCubugu button").forEach(b => b.classList.remove("aktif"));
  $("#aracIpucu").hidden = true;
  $("#harita").classList.remove("cizim-kipi");
  D.harita?.doubleClickZoom.enable();
}
function cizimleriTemizle() { aracKapat(); D.cizim?.grup?.clearLayers(); $("#profilCekmece").hidden = true; }
function mesafeHesap(pts) { let s = 0; for (let i = 1; i < pts.length; i++) s += L.latLng(pts[i - 1]).distanceTo(pts[i]); return s; }
function alanHesap(pts) {
  if (pts.length < 3) return 0;
  const lat0 = pts.reduce((a, p) => a + p.lat, 0) / pts.length, kx = 111320 * Math.cos(lat0 * Math.PI / 180), ky = 110574;
  let s = 0;
  for (let i = 0; i < pts.length; i++) { const a = pts[i], b = pts[(i + 1) % pts.length]; s += (a.lng * kx) * (b.lat * ky) - (b.lng * kx) * (a.lat * ky); }
  return Math.abs(s) / 2;
}
const mesafeYaz = m => ftMi() ? (m * FT > 5280 ? `${nf(m * FT / 5280, 2)} mi` : `${nf(m * FT, 0)} ft`) : (m > 1000 ? `${nf(m / 1000, 2)} km` : `${nf(m, 1)} m`);
const alanYaz = a => a > 10000 ? `${nf(a, 0)} m² (${nf(a / 10000, 2)} ha)` : `${nf(a, 0)} m²`;
function cizimOnizle(ll) {
  const c = D.cizim; if (!c || !c.noktalar.length) return;
  const pts = [...c.noktalar, ll];
  if (c.gecici) c.grup.removeLayer(c.gecici);
  const stil = { color: D.arac === "alan3d" ? "#22d3ee" : "#facc15", weight: 2.5, dashArray: "5 5", interactive: false };
  const dik = D.arac === "alan3d" && UC.kip === "dikdortgen";
  if (dik) c.gecici = L.rectangle([c.noktalar[0], ll], { ...stil, fillOpacity: .1 }).addTo(c.grup);
  else c.gecici = (D.arac === "alan" || D.arac === "alan3d" ? L.polygon(pts, { ...stil, fillOpacity: .12 }) : L.polyline(pts, stil)).addTo(c.grup);
  const met = dik ? alanYaz(alanHesap([c.noktalar[0], L.latLng(c.noktalar[0].lat, ll.lng), ll, L.latLng(ll.lat, c.noktalar[0].lng)]))
    : D.arac === "alan" || D.arac === "alan3d" ? alanYaz(alanHesap(pts)) : mesafeYaz(mesafeHesap(pts));
  c.gecici.bindTooltip(met, { permanent: true, direction: "right", className: "olcu-etiket" }).openTooltip(ll);
}
function aracTik(ll) {
  if (D.arac === "not") { notPenceresi({ lat: ll.lat, lon: ll.lng }); aracKapat(); return; }
  if (D.arac === "alan3d" && UC.kip === "dikdortgen" && D.cizim.noktalar.length === 1) {       // ikinci kose: dikdortgen tamam
    const a = D.cizim.noktalar[0];
    if (Math.abs(a.lat - ll.lat) < 1e-6 || Math.abs(a.lng - ll.lng) < 1e-6) return;
    D.cizim.noktalar = [a, L.latLng(a.lat, ll.lng), ll, L.latLng(ll.lat, a.lng)];
    aracBitir();
    return;
  }
  D.cizim.noktalar.push(ll);
  L.circleMarker(ll, { radius: 4, color: "#111", weight: 1, fillColor: "#facc15", fillOpacity: 1, interactive: false }).addTo(D.cizim.grup);
}
async function aracBitir() {
  const a = D.arac, c = D.cizim;
  if (a === "alan3d") {
    const pts = c.noktalar.slice();
    if (c.gecici) c.grup.removeLayer(c.gecici);
    const dik = UC.kip === "dikdortgen";
    aracKapat();
    if (pts.length < (dik ? 4 : 3)) { bildir(t("Alan için en az üç köşe gerekli"), true); return; }
    ucAlanSecildi(pts, dik ? "dikdortgen" : "cokgen");
    return;
  }
  if (!c || c.noktalar.length < 2) { aracKapat(); return; }
  if (c.gecici) c.grup.removeLayer(c.gecici);
  const pts = c.noktalar;
  const stil = { color: a === "profil" ? "#22d3ee" : "#facc15", weight: 3, interactive: false };
  let sekil, met;
  if (a === "alan") { sekil = L.polygon(pts, { ...stil, fillOpacity: .15 }); met = `${t("Alan")}: ${alanYaz(alanHesap(pts))} · ${t("çevre")} ${mesafeYaz(mesafeHesap([...pts, pts[0]]))}`; }
  else { sekil = L.polyline(pts, stil); met = mesafeYaz(mesafeHesap(pts)); }
  sekil.addTo(c.grup).bindTooltip(met, { permanent: true, direction: "center", className: "olcu-etiket" });
  aracKapat();
  if (a === "profil") await profilGoster(pts);
}
let profilVeri = null;
async function profilGoster(pts) {
  try {
    const yol = pts.map(p => `${p.lat.toFixed(7)},${p.lng.toFixed(7)}`).join(";");
    const r = await api(purl(`profil?yol=${encodeURIComponent(yol)}`));
    profilVeri = r;
    $("#kesitCekmece").hidden = true;
    $("#profilCekmece").hidden = false;
    const ol = r.derinlik.filter(v => v != null);
    $("#pfBilgi").textContent = `${t("uzunluk")} ${mesafeYaz(r.uzunluk)} · ${t("en derin")} ${uz(Math.max(...ol), 2)} · ${t("ortalama")} ${uz(ol.reduce((a, b) => a + b, 0) / (ol.length || 1), 2)}`;
    D.profilGrafik?.destroy();
    const v = (k) => r.mesafe.map((x, i) => ({ x: uzc(x), y: r.kaynak[i] === k ? uzc(r.derinlik[i]) : null }));
    D.profilGrafik = new Chart($("#pfGrafik"), {
      type: "line",
      data: { datasets: [
        { label: t("Ölçülen / ara değer"), data: v(1), borderColor: "#22d3ee", backgroundColor: "rgba(34,211,238,.18)", fill: "start", pointRadius: 0, borderWidth: 2, spanGaps: false },
        { label: t("Tahmin (uydu analizi)"), data: v(2), borderColor: "#fbbf24", backgroundColor: "rgba(251,191,36,.12)", fill: "start", pointRadius: 0, borderWidth: 1.6, borderDash: [5, 4], spanGaps: false }] },
      options: { responsive: true, maintainAspectRatio: false, animation: false, parsing: false,
        interaction: { mode: "nearest", axis: "x", intersect: false },
        plugins: { legend: { labels: { boxWidth: 12 } }, tooltip: { callbacks: { title: it => `${nf(it[0].parsed.x, 1)} ${birim()}`, label: it => `${nf(it.parsed.y, 2)} ${birim()}` } } },
        scales: { x: { type: "linear", title: { display: true, text: `${t("Mesafe")} (${birim()})` } }, y: { reverse: true, min: 0, title: { display: true, text: `${t("Derinlik")} (${birim()})` } } } },
    });
  } catch (e) { bildir(e.message, true); }
}
function profilCsv() {
  if (!profilVeri) return;
  const s = "mesafe_m;derinlik_m;kaynak\n" + profilVeri.mesafe.map((m, i) => `${m};${profilVeri.derinlik[i] ?? ""};${["yok", "olcum", "tahmin"][profilVeri.kaynak[i]]}`).join("\n");
  const u = URL.createObjectURL(new Blob(["﻿" + s], { type: "text/csv" }));
  const a = document.createElement("a"); a.href = u; a.download = "derinlik_profili.csv"; a.click(); setTimeout(() => URL.revokeObjectURL(u), 2000);
}
function notPenceresi(n) {
  const yeni = !n.id;
  const renkler = ["#f59e0b", "#ef4444", "#22c55e", "#3b82f6", "#a855f7", "#f8fafc"];
  const p = pencereAc({
    baslik: t(yeni ? "Not ekle" : "Notu düzenle"),
    govde: `<div class="form">
      <label>${t("Başlık")}<input id="nBaslik" maxlength="120" value="${esc(n.baslik || "")}" placeholder="${esc(t("örn. İskele, kaya, numune alındı"))}"></label>
      <label>${t("Açıklama")}<textarea id="nMetin" rows="4" maxlength="1000">${esc(n.metin || "")}</textarea></label>
      <div class="renk-sec">${renkler.map(r => `<button type="button" data-renk="${r}" style="--renk:${r}" class="${(n.renk || renkler[0]) === r ? "aktif" : ""}"></button>`).join("")}</div>
      <small class="ince">${n.lat.toFixed(6)}, ${n.lon.toFixed(6)}</small></div>`,
    alt: `<button class="btn hayalet" data-iptal>${t("Vazgeç")}</button><button class="btn" data-kaydet>${t("Kaydet")}</button>`,
  });
  let renk = n.renk || renkler[0];
  $$("[data-renk]", p).forEach(b => b.onclick = () => { renk = b.dataset.renk; $$("[data-renk]", p).forEach(x => x.classList.toggle("aktif", x === b)); });
  $("[data-iptal]", p).onclick = pencereKapat;
  $("[data-kaydet]", p).onclick = async () => {
    const kayit = { ...n, baslik: $("#nBaslik").value.trim(), metin: $("#nMetin").value.trim(), renk };
    if (yeni) D.notlar.push(kayit); else D.notlar = D.notlar.map(x => x.id === n.id ? kayit : x);
    pencereKapat();
    await notlariKaydet();
  };
  setTimeout(() => $("#nBaslik")?.focus(), 30);
}
async function notlariKaydet() {
  try {
    D.notlar = await jsonGonder(purl("notlar"), D.notlar);
    D.acikKatman.add("notlar");
    if (D.katmanlar.notlar) { D.harita.removeLayer(D.katmanlar.notlar); delete D.katmanlar.notlar; }
    katmanlariKur();
    bildir(t("Notlar kaydedildi"));
  } catch (e) { bildir(e.message, true); }
}

// ------------------------------------------------------------------ kesit
async function kesitGetir(satir, genislik, palet, img, cnv, yuk) {
  const no = ++D.kesitIstek;
  yuk?.classList.add("acik");
  try {
    const r = await fetch(purl(`kesit?merkez=${satir}&genislik=${genislik}&palet=${palet}`));
    if (!r.ok) throw new Error(t("Kesit alınamadı"));
    const bilgi = JSON.parse(r.headers.get("X-Kesit")), dip = JSON.parse(r.headers.get("X-Dip"));
    const blob = await r.blob();
    if (no !== D.kesitIstek && img.id !== "kcImg") return;
    const u = URL.createObjectURL(blob);
    await new Promise(res => { img.onload = res; img.src = u; });
    URL.revokeObjectURL(img.dataset.u || ""); img.dataset.u = u;
    if (cnv.id === "sonarCanvas") D.sonKesit = { bilgi, dip, satir };
    kesitUstCiz(cnv, bilgi, dip, satir);
    return bilgi;
  } catch (e) { bildir(e.message, true); }
  finally { yuk?.classList.remove("acik"); }
}
function kesitUstCiz(cnv, b, dip, satir) {
  const W = cnv.clientWidth, H = cnv.clientHeight, dpr = devicePixelRatio || 1;
  cnv.width = W * dpr; cnv.height = H * dpr;
  const c = cnv.getContext("2d"); c.scale(dpr, dpr); c.clearRect(0, 0, W, H);
  const dmaxB = uzc(b.dmax);
  c.font = "11px system-ui"; c.fillStyle = "rgba(255,255,255,.75)"; c.strokeStyle = "rgba(255,255,255,.12)";
  const adim = dmaxB > 24 ? 5 : dmaxB > 12 ? 2 : dmaxB > 5 ? 1 : 0.5;
  for (let z = adim; z < dmaxB; z += adim) {
    const y = z / dmaxB * H;
    c.beginPath(); c.moveTo(0, y); c.lineTo(W, y); c.stroke();
    c.fillText(`${nf(z, adim < 1 ? 1 : 0)} ${birim()}`, 6, y - 3);
  }
  const sx = s => (s - b.a0) / (b.a1 - b.a0) * W, sy = z => z / b.dmax * H;
  if (cnv.id === "sonarCanvas" && D.duzenle) {
    // cihaz / duzeltilmis dip cizgisi
    c.strokeStyle = "rgba(250,204,21,.9)"; c.lineWidth = 1.4; c.beginPath();
    let ilk = true; dip.forEach((z, i) => { if (z == null) { ilk = true; return; } const x = sx(b.a0 + i * (b.adim || 1)), y = sy(z); ilk ? c.moveTo(x, y) : c.lineTo(x, y); ilk = false; });
    c.stroke();
    const dz = D.duz || { dip: [], silinen: [] };
    c.fillStyle = "rgba(248,113,113,.28)";
    for (const [a0, a1] of dz.silinen) { const x0 = sx(Math.min(a0, a1)), x1 = sx(Math.max(a0, a1) + 1); if (x1 > 0 && x0 < W) c.fillRect(x0, 0, x1 - x0, H); }
    c.strokeStyle = "#4ade80"; c.lineWidth = 2.2;
    for (const cz of dz.dip) { c.beginPath(); cz.noktalar.forEach(([s, z], i) => i ? c.lineTo(sx(s), sy(z)) : c.moveTo(sx(s), sy(z))); c.stroke(); }
    const ak = duzenleAktif;
    if (ak?.noktalar?.length) {
      if (ak.kip === "ciz") { c.strokeStyle = "#86efac"; c.setLineDash([3, 3]); c.beginPath(); ak.noktalar.forEach(([s, z], i) => i ? c.lineTo(sx(s), sy(z)) : c.moveTo(sx(s), sy(z))); c.stroke(); c.setLineDash([]); }
      else { const s0 = ak.noktalar[0][0], s1 = ak.noktalar[ak.noktalar.length - 1][0]; c.fillStyle = "rgba(248,113,113,.4)"; c.fillRect(sx(Math.min(s0, s1)), 0, Math.abs(sx(s1) - sx(s0)), H); }
    }
  }
  const x = sx(satir);
  c.strokeStyle = "rgba(34,211,238,.9)"; c.setLineDash([4, 4]); c.lineWidth = 1.5;
  c.beginPath(); c.moveTo(x, 0); c.lineTo(x, H); c.stroke(); c.setLineDash([]);
}

// ------------------------------------------------------------------ sonar sekmesi
function satirBilgi(satir) {
  const z = D.veri.zaman;
  let i = z.satir.findIndex(s => s >= satir); if (i < 0) i = z.satir.length - 1;
  return { t: z.t[i], dep: z.dep[i] };
}
let sonarZam;
function sonarGit(satir, hemen = false) {
  D.sonarSatir = Math.max(0, Math.min(D.veri.ozet.toplam_satir - 1, Math.round(satir)));
  $("#zamanCubuk").value = D.sonarSatir;
  const b = satirBilgi(D.sonarSatir);
  $("#okZaman").textContent = `${sureYaz(b.t)} ${t("dk")}`;
  $("#okDerinlik").textContent = b.dep == null ? "–" : uz(b.dep, 2);
  $("#okPing").textContent = nf(D.sonarSatir);
  genelCiz();
  clearTimeout(sonarZam);
  const f = () => kesitGetir(D.sonarSatir, +$("#genislik").value, $("#palet").value, $("#sonarImg"), $("#sonarCanvas"), $("#sonarYuk"));
  return hemen ? f() : (sonarZam = setTimeout(f, 110));
}
async function oynat() {
  D.oynuyor = !D.oynuyor;
  $("#oynatIkon").setAttribute("d", D.oynuyor ? "M7 5h4v14H7zM13 5h4v14h-4z" : "M8 5v14l11-7z");
  while (D.oynuyor && D.sekme === "sonar") {
    const g = +$("#genislik").value;
    if (D.sonarSatir >= D.veri.ozet.toplam_satir - 1) { D.oynuyor = false; break; }
    const t0 = performance.now();
    await sonarGit(D.sonarSatir + g / 4, true);
    await new Promise(r => setTimeout(r, Math.max(0, 350 - (performance.now() - t0))));
  }
  D.oynuyor = false; $("#oynatIkon").setAttribute("d", "M8 5v14l11-7z");
}
function genelCiz() {
  const cnv = $("#genelCanvas"); if (!cnv) return;
  const W = cnv.clientWidth, H = cnv.clientHeight, dpr = devicePixelRatio || 1;
  cnv.width = W * dpr; cnv.height = H * dpr;
  const c = cnv.getContext("2d"); c.scale(dpr, dpr);
  const z = D.veri.zaman, tmax = z.t[z.t.length - 1], dmax = D.veri.ozet.kesit_derinlik_max;
  const g = c.createLinearGradient(0, 0, 0, H); g.addColorStop(0, "#0e2440"); g.addColorStop(1, "#06101d");
  c.fillStyle = g; c.fillRect(0, 0, W, H);
  c.beginPath(); c.moveTo(0, H);
  z.t.forEach((tt, i) => { if (z.dep[i] != null) c.lineTo(tt / tmax * W, z.dep[i] / dmax * H); });
  c.lineTo(W, H); c.closePath();
  const g2 = c.createLinearGradient(0, 0, 0, H); g2.addColorStop(0, "#b45309"); g2.addColorStop(1, "#3b1d06");
  c.fillStyle = g2; c.fill();
  c.strokeStyle = "#fbbf24"; c.lineWidth = 1; c.beginPath();
  let ilk = true; z.t.forEach((tt, i) => { if (z.dep[i] == null) { ilk = true; return; } const x = tt / tmax * W, y = z.dep[i] / dmax * H; ilk ? c.moveTo(x, y) : c.lineTo(x, y); ilk = false; });
  c.stroke();
  const b = satirBilgi(D.sonarSatir), x = b.t / tmax * W;
  const gen = +$("#genislik").value / D.veri.ozet.ping_hz / 60 / tmax * W;
  c.fillStyle = "rgba(34,211,238,.18)"; c.fillRect(x - gen / 2, 0, gen, H);
  c.strokeStyle = "#22d3ee"; c.lineWidth = 2; c.beginPath(); c.moveTo(x, 0); c.lineTo(x, H); c.stroke();
  c.fillStyle = "rgba(255,255,255,.6)"; c.font = "11px system-ui";
  for (let m = 0; m <= tmax; m += tmax > 30 ? 10 : 5) c.fillText(`${m} ${t("dk")}`, m / tmax * W + 3, H - 5);
}
function sonarKur() {
  const gb = $(".genel-bakis");
  if (!$("#genelCanvas")) {
    gb.innerHTML = `<canvas id="genelCanvas" style="display:block;width:100%;height:120px"></canvas>`;
    gb.style.background = "none";
    $("#genelCanvas").onclick = e => {
      const r = e.target.getBoundingClientRect(), z = D.veri.zaman;
      const tt = (e.clientX - r.left) / r.width * z.t[z.t.length - 1];
      let i = z.t.findIndex(v => v >= tt); if (i < 0) i = z.t.length - 1;
      sonarGit(z.satir[i]);
    };
  }
  gb.previousElementSibling.innerHTML = `${esc(t("Tüm kayıt — derinlik profili"))} <span class="ince">${esc(t("tıkla: o ana git"))}</span>`;
  sonarGit(D.sonarSatir, true);
}
function sonarBagla() {
  $("#zamanCubuk").oninput = e => sonarGit(+e.target.value);
  $("#genislik").onchange = () => sonarGit(D.sonarSatir, true);
  $("#palet").onchange = () => sonarGit(D.sonarSatir, true);
  $("#oynat").onclick = oynat;
  $("#sonarImg").parentElement.onclick = e => {
    if (D.duzenle) return;
    const r = e.currentTarget.getBoundingClientRect(), g = +$("#genislik").value;
    sonarGit(D.sonarSatir + ((e.clientX - r.left) / r.width - 0.5) * g);
  };
  addEventListener("keydown", e => {
    if (!$("#perde").hidden) { if (e.key === "Escape") pencereKapat(); return; }
    if (e.key === "Escape" && D.arac) { aracKapat(); return; }
    if (e.key === "Enter" && D.arac && D.cizim) { aracBitir(); return; }
    if (D.sekme !== "sonar" || e.target.matches("input[type=text],input:not([type]),select,textarea,input[type=search],input[type=number]")) return;
    const g = +$("#genislik").value;
    if (e.key === "ArrowRight") { e.preventDefault(); sonarGit(D.sonarSatir + g / 4); }
    if (e.key === "ArrowLeft") { e.preventDefault(); sonarGit(D.sonarSatir - g / 4); }
    if (e.key === " ") { e.preventDefault(); oynat(); }
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "z" && D.duzenle) { e.preventDefault(); duzGeriAl(); }
  });
  addEventListener("resize", () => { if (D.sekme === "sonar") { genelCiz(); if (D.sonKesit) kesitUstCiz($("#sonarCanvas"), D.sonKesit.bilgi, D.sonKesit.dip, D.sonKesit.satir); } });
  duzenleBagla();
}

// ------------------------------------------------------------------ elle duzeltme (sonar)
let duzenleAktif = null;
async function duzenleAc() {
  if (calisiyorMu()) { bildir(t("Çalışan analiz varken düzeltme yapılamaz."), true); return; }
  try { D.duz = await api(purl("duzeltmeler")); } catch { D.duz = { dip: [], silinen: [] }; }
  D.duzGecmis = []; D.duzenle = true;
  $("#duzenleCubugu").hidden = false; $("#duzenleBtn").classList.add("aktif");
  $("#sonarCanvas").classList.add("duzenleniyor");
  duzenleYenile();
}
function duzenleKapat(sessiz = false) {
  if (!sessiz && D.duzGecmis.length && !confirm(t("Kaydedilmemiş düzeltmeler var. Kapatılsın mı?"))) return;
  D.duzenle = false; duzenleAktif = null;
  $("#duzenleCubugu").hidden = true; $("#duzenleBtn").classList.remove("aktif");
  $("#sonarCanvas").classList.remove("duzenleniyor");
  if (D.sonKesit) kesitUstCiz($("#sonarCanvas"), D.sonKesit.bilgi, D.sonKesit.dip, D.sonKesit.satir);
}
function duzenleYenile() {
  const d = D.duz || { dip: [], silinen: [] };
  $("#duzenleBilgi").textContent = `${d.dip.length} ${t("çizilen dip")} · ${d.silinen.length} ${t("silinen aralık")}${D.duzGecmis.length ? " · " + t("kaydedilmedi") : ""}`;
  if (D.sonKesit) kesitUstCiz($("#sonarCanvas"), D.sonKesit.bilgi, D.sonKesit.dip, D.sonKesit.satir);
}
function duzGeriAl() { if (!D.duzGecmis.length) return; D.duz = D.duzGecmis.pop(); duzenleYenile(); }
function duzenleBagla() {
  const cnv = $("#sonarCanvas");
  const konum = e => {
    const r = cnv.getBoundingClientRect(), b = D.sonKesit.bilgi;
    const fx = Math.max(0, Math.min(1, (e.clientX - r.left) / r.width)), fy = Math.max(0, Math.min(1, (e.clientY - r.top) / r.height));
    return [Math.round(b.a0 + fx * (b.a1 - b.a0)), Math.round(fy * b.dmax * 1000) / 1000];
  };
  cnv.addEventListener("pointerdown", e => {
    if (!D.duzenle || !D.sonKesit) return;
    e.preventDefault(); cnv.setPointerCapture(e.pointerId);
    duzenleAktif = { kip: D.duzKip, noktalar: [konum(e)] };
  });
  cnv.addEventListener("pointermove", e => {
    if (!duzenleAktif) return;
    const p = konum(e), son = duzenleAktif.noktalar[duzenleAktif.noktalar.length - 1];
    if (p[0] !== son[0]) duzenleAktif.noktalar.push(p);
    kesitUstCiz(cnv, D.sonKesit.bilgi, D.sonKesit.dip, D.sonKesit.satir);
  });
  cnv.addEventListener("pointerup", () => {
    if (!duzenleAktif) return;
    const a = duzenleAktif; duzenleAktif = null;
    if (a.noktalar.length < 2) { duzenleYenile(); return; }
    D.duzGecmis.push(JSON.parse(JSON.stringify(D.duz)));
    if (a.kip === "ciz") {
      const m = new Map(); a.noktalar.forEach(([s, z]) => m.set(s, z));
      D.duz.dip.push({ noktalar: [...m.entries()].sort((x, y) => x[0] - y[0]) });
    } else {
      const s = a.noktalar.map(p => p[0]); D.duz.silinen.push([Math.min(...s), Math.max(...s)]);
    }
    duzenleYenile();
  });
  $("#duzenleBtn").onclick = () => (D.duzenle ? duzenleKapat() : duzenleAc());
  $$("#duzenleKip button").forEach(b => b.onclick = () => { D.duzKip = b.dataset.k; $$("#duzenleKip button").forEach(x => x.classList.toggle("aktif", x === b)); });
  $("#geriAlBtn").onclick = duzGeriAl;
  $("#duzTemizleBtn").onclick = () => {
    if (!D.duz.dip.length && !D.duz.silinen.length) return;
    if (!confirm(t("Bu projedeki tüm elle düzeltmeler kaldırılsın mı?"))) return;
    D.duzGecmis.push(JSON.parse(JSON.stringify(D.duz))); D.duz = { dip: [], silinen: [] }; duzenleYenile();
  };
  $("#duzKapatBtn").onclick = () => duzenleKapat();
  $("#duzKaydetBtn").onclick = async () => {
    const b = $("#duzKaydetBtn"); b.disabled = true; b.textContent = t("Kaydediliyor…");
    try {
      D.duz = await jsonGonder(purl("duzeltmeler"), D.duz);
      D.duzGecmis = [];
      bildir(t("Düzeltmeler kaydedildi. Haritaların güncellenmesi için 'Yeniden hesapla'yı kullanın."));
      await sonarGit(D.sonarSatir, true);
      duzenleYenile();
      durumGuncelle();
    } catch (e) { bildir(e.message, true); }
    finally { b.disabled = false; b.textContent = t("Kaydet"); }
  };
}

// ------------------------------------------------------------------ grafikler
function grafikKur() {
  if (D.grafikHazir || !D.veri.zaman) return;
  D.grafikler.forEach(g => g.destroy()); D.grafikler = [];
  const z = D.veri.zaman;
  Chart.defaults.color = "#8b9ab3"; Chart.defaults.borderColor = "rgba(148,170,210,.12)";
  Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
  const ortak = (br, ters = false) => ({
    responsive: true, maintainAspectRatio: false, animation: false, parsing: false, normalized: true,
    interaction: { mode: "nearest", axis: "x", intersect: false },
    plugins: { legend: { display: false }, tooltip: { callbacks: { title: it => `${sureYaz(it[0].parsed.x)}. ${t("dk")}`, label: it => `${nf(it.parsed.y, 2)} ${br}` } },
      decimation: { enabled: true, algorithm: "min-max" } },
    scales: { x: { type: "linear", title: { display: true, text: t("Kayıt süresi (dk)") } }, y: { reverse: ters, title: { display: true, text: br } } },
    onClick: (e, el, ch) => { const x = ch.scales.x.getValueForPixel(e.x); let i = z.t.findIndex(v => v >= x); if (i < 0) i = z.t.length - 1; D.sonarSatir = z.satir[i]; sekmeAc("sonar"); },
  });
  const seri = (k, f = v => v) => z.t.map((tt, i) => ({ x: tt, y: z[k][i] == null ? null : f(z[k][i]) })).filter(p => p.y != null);
  const yap = (id, k, renk, br, ters, f) => new Chart($(id), {
    type: "line", data: { datasets: [{ data: seri(k, f), borderColor: renk, borderWidth: 1.4, pointRadius: 0, fill: ters ? "start" : "origin",
      backgroundColor: renk + "22", tension: 0 }] }, options: ortak(br, ters) });
  D.grafikler = [yap("#gDerinlik", "dep", "#22d3ee", birim(), true, uzc), yap("#gHiz", "hiz", "#fbbf24", "km/h"), yap("#gSicaklik", "sic", "#f87171", "°C")];
  hacimGrafik();
  D.grafikHazir = true;
}
function hacimGrafik() {
  const h = D.veri.hacimTablo;
  $("#hacimKart").hidden = !h;
  if (!h) return;
  const tb = h.tablo, kot = tb.kot_m.map(uzc);
  $("#hacimKapsam").textContent = `${t(h.kapsam)} · ${t("su yüzeyi kotu")} ${uz(h.su_kotu, 2)}`;
  D.grafikler.push(new Chart($("#gHacim"), {
    type: "line",
    data: { datasets: [
      { label: t("Alan (m²)"), data: tb.alan_m2.map((a, i) => ({ x: a, y: kot[i] })), borderColor: "#22d3ee", xAxisID: "x", pointRadius: 0, borderWidth: 2 },
      { label: t("Hacim (m³)"), data: tb.hacim_m3.map((a, i) => ({ x: a, y: kot[i] })), borderColor: "#fbbf24", xAxisID: "x2", pointRadius: 0, borderWidth: 2 }] },
    options: { responsive: true, maintainAspectRatio: false, animation: false, parsing: false,
      interaction: { mode: "nearest", axis: "y", intersect: false },
      plugins: { legend: { labels: { boxWidth: 12 } }, tooltip: { callbacks: { title: it => `${t("Kot")} ${nf(it[0].parsed.y, 2)} ${birim()}`, label: it => `${it.dataset.label}: ${nf(it.parsed.x)}` } } },
      scales: { x: { type: "linear", position: "bottom", title: { display: true, text: t("Alan (m²)") }, ticks: { color: "#22d3ee" } },
        x2: { type: "linear", position: "top", title: { display: true, text: t("Hacim (m³)") }, ticks: { color: "#fbbf24" }, grid: { drawOnChartArea: false } },
        y: { title: { display: true, text: `${t("Kot")} (${birim()})` } } } },
  }));
  const satirlar = tb.kot_m.map((k, i) => `<tr><td>${nf(uzc(k), 2)}</td><td>${nf(uzc(tb.su_derinligi_m[i]), 2)}</td><td>${nf(tb.alan_m2[i])}</td><td>${nf(tb.hacim_m3[i])}</td></tr>`).reverse().join("");
  $("#hacimTablo").innerHTML = `<table><thead><tr><th>${t("Kot")} (${birim()})</th><th>${t("Derinlik")} (${birim()})</th><th>${t("Alan")} (m²)</th><th>${t("Hacim")} (m³)</th></tr></thead><tbody>${satirlar}</tbody></table>
    <div class="ht-alt"><span class="ince">${t("Toplam")}: ${nf(h.toplam_hacim_m3)} ± ${nf(h.hacim_belirsizlik_m3)} m³</span><a class="indirme" data-yol="hacim/kot_alan_hacim.csv" data-tur="csv" href="${purl("dosya/hacim/kot_alan_hacim.csv")}?indir=1"><em>csv</em>${t("Tabloyu indir")}</a></div>`;
}

// ------------------------------------------------------------------ analiz kartlari
const ANALIZ_IKON = { temel: "◎", zemin: "▦", uydu: "◰", taramalar: "≋", dogrulama: "✓", degisim: "⇅", disari: "⌘", rapor: "⎙" };
const ANALIZ_ACIKLAMA = {
  temel: "RSD dosyasını çözer; düzeltmeleri uygular. Rota, derinlik haritası, eş derinlik çizgileri, sonar görüntüleri, kot–alan–hacim tablosu ve belirsizlik haritası.",
  zemin: "Dip yankısının şeklinden sertlik, penetrasyon ve sönümlenme ölçer; zemini 3 göreli sınıfa ayırır ve dip numunesi noktaları önerir (GPX).",
  uydu: "Uydu görüntüsünden kıyı çizgisini çıkarır; tüm su alanı için hacim, dip eğimi, kapsama ve eksik alanlar için yeni tarama rotası (GPX). İnternet gerekir.",
  taramalar: "Su kolonunda balık ve gaz kabarcığı izleri, dipte kaya / batık nesne ve su bitkisi örtüsü taraması.",
  dogrulama: "Çubukla ölçülen derinlikleri ve dip numunelerini sonarla karşılaştırır; doğruluk (RMSE) verir, kalibrasyon ve sınıf adları önerir.",
  degisim: "Aynı göletin başka tarihteki taramasıyla karşılaştırır: dip kotu değişimi, sediman birikimi / oyulma haritası, yıllık m³.",
  disari: "Seçilen koordinat sisteminde GeoTIFF, Shapefile, GeoJSON, KML (Google Earth), DXF (AutoCAD / NetCAD) ve XYZ dosyaları; tek zip.",
  rapor: "Çalışmış tüm analizleri kapak, firma bilgisi ve imza alanıyla tek rapora toplar: PDF ve HTML.",
};
const ANALIZ_SURE = { temel: "~1 dk", zemin: "~2 dk", uydu: "~1 dk", taramalar: "~1 dk", dogrulama: "~5 sn", degisim: "~5 sn", disari: "~10 sn", rapor: "~20 sn" };
function analizSonuc(tur) {
  const v = D.veri, o = [];
  if (tur === "temel" && v.ozet) { o.push([t("Derinlik"), `${uz(v.ozet.derinlik_min, 1)}–${uz(v.ozet.derinlik_max, 1)}`], [t("Haritalanan"), `${nf(v.ozet.haritalanan_alan_m2)} m²`]);
    if (v.hacimTablo) o.push([t("Hacim"), `${nf(v.hacimTablo.toplam_hacim_m3)} m³`], [t("Belirsizlik"), `±${nf(v.hacimTablo.sigma_medyan_cm)} cm`]); }
  if (tur === "zemin" && v.kz) v.kz.siniflar.slice(0, 2).forEach(s => o.push([s.ad.split(" (")[0], `%${nf(s.alan_yuzde)}`]));
  if (tur === "uydu" && v.hacim) o.push([t("Toplam hacim"), `${nf(v.hacim.tum_golet_hacmi_m3_kiyi0m)}–${nf(v.hacim["tum_golet_hacmi_m3_kiyi0.5m"])} m³`], [t("Ölçülen"), `%${nf(v.hacim.olculen_alan_yuzde)}`],
    [t("Yeni rota"), `${v.hacim.yeni_rota_hat_sayisi} ${t("hat")} · ${nf(v.hacim.yeni_rota_sure_dk)} ${t("dk")}`], [t("Dip eğimi"), `${nf(v.hacim.egim_medyan_derece, 1)}°`]);
  if (tur === "taramalar" && v.tar) o.push([t("Balık izi"), nf(v.tar.balik)], [t("Gaz kabarcığı"), v.tar.kabarcik ? nf(v.tar.kabarcik) : t("yok")],
    [t("Sert nokta"), v.tar.sert_nokta ? nf(v.tar.sert_nokta) : t("yok")], [t("Bitki kaplama"), `%${nf(v.tar.bitki_kaplama_ort_yuzde, 1)}`]);
  if (tur === "dogrulama" && v.dogrulama) {
    const d = v.dogrulama.derinlik, z = v.dogrulama.zemin;
    if (d?.rmse_m != null) o.push(["RMSE", `${nf(d.rmse_m * 100, 1)} cm`], [t("Ortalama fark"), `${nf(d.ortalama_fark_m * 100, 1)} cm`]);
    else if (d?.uyari) o.push([t("Derinlik"), t(d.uyari)]);
    if (z?.kullanilan) o.push([t("Zemin uyumu"), `%${nf(z.uyum_yuzde)}`], [t("Numune"), nf(z.kullanilan)]);
  }
  if (tur === "degisim" && v.degisim) { const g = v.degisim; o.push([t("Net"), `${nf(g.net_m3)} m³`], [t("Yıllık"), g.yillik_net_m3 == null ? "–" : `${nf(g.yillik_net_m3)} m³`],
    [t("Birikim"), `${nf(g.birikim_m3)} m³`], [t("Oyulma"), `${nf(g.oyulma_m3)} m³`]); }
  if (tur === "disari" && v.disari) o.push([t("Koordinat"), `EPSG:${v.disari.epsg}`], [t("Dosya"), nf(v.disari.dosya_sayisi)]);
  return o;
}
function analizEk(tur, d) {
  const p = D.proje, ep = p.etkin_parametreler || {};
  if (tur === "dogrulama") {
    const dg = D.veri.dogrulama;
    let h = `<div class="ak-ek"><button class="btn hayalet kucuk" data-ek="sablon">${t("Şablonu indir")}</button>
      <button class="btn hayalet kucuk" data-ek="csv">${t(p.dogrulama_var ? "Yeni CSV yükle" : "CSV yükle")}</button></div>`;
    if (d === "bitti" && dg && ((dg.derinlik?.oneri) || (dg.zemin?.oneri && Object.keys(dg.zemin.oneri).length))) {
      const on = dg.derinlik?.oneri;
      h += `<div class="oneri"><b>${t("Kalibrasyon önerisi")}</b>
        ${on ? `<label><input type="checkbox" data-kal="derinlik" checked> ${t("Batma payı")} ${uz(on.batma_payi, 2)}${on.ses_hizi_elle ? `, ${t("ses hızı")} ${nf(on.ses_hizi_elle)} m/s` : ""}</label>` : ""}
        ${dg.zemin?.oneri && Object.keys(dg.zemin.oneri).length ? `<label><input type="checkbox" data-kal="zemin" checked> ${t("Zemin sınıflarına numune adlarını ver")} (${Object.entries(dg.zemin.oneri).map(([k, o]) => `${+k + 1}: ${esc(o.ad)}`).join(", ")})</label>` : ""}
        <button class="btn kucuk" data-ek="kalibre">${t("Uygula ve yeniden hesapla")}</button></div>`;
    }
    return h;
  }
  if (tur === "degisim") {
    const diger = D.projeler.filter(x => x.id !== p.id);
    return `<div class="ak-ek"><label class="sec tam">${t("Karşılaştırılacak tarama")}
      <select data-ek="degisim-proje"><option value="">${t("— proje seç —")}</option>${diger.map(x => `<option value="${x.id}" ${ep.degisim_proje === x.id ? "selected" : ""}>${esc(x.ad)}${x.ozet ? ` (${x.ozet.tarih})` : ""}</option>`).join("")}</select></label>
      ${d === "bitti" && D.veri.degisim?.su_seviyesi_uyari ? `<small class="uyari-not">${esc(t(D.veri.degisim.tek_kot ? "Su yüzeyi kotu yalnızca bir projede girilmiş; iki tarihte su seviyesi aynı kabul edildi." : "Su yüzeyi kotu girilmediği için iki tarihte su seviyesi aynı kabul edildi."))}</small>` : ""}</div>`;
  }
  if (tur === "disari") {
    const k = D.ayarMeta?.koordinatlar || {};
    return `<div class="ak-ek"><label class="sec tam">${t("Koordinat sistemi")}
      <select data-ek="koordinat">${Object.entries(k).map(([a, b]) => `<option value="${a}" ${D.ayar?.koordinat === a ? "selected" : ""}>${esc(t(b))}</option>`).join("")}</select></label>
      ${d === "bitti" && D.veri.disari ? `<div class="ak-ek"><button class="btn kucuk" data-ek="zip">${t("ZIP'i kaydet")}</button>${masaustu() ? `<button class="btn hayalet kucuk" data-ek="disari-klasor">${t("Klasörü aç")}</button>` : ""}</div>` : ""}</div>`;
  }
  if (tur === "rapor" && d === "bitti") {
    return `<div class="ak-ek"><button class="btn kucuk" data-ek="pdf">${t("PDF'i aç")}</button><button class="btn hayalet kucuk" data-ek="html">${t("HTML'i aç")}</button></div>`;
  }
  return "";
}
function analizKartlariCiz() {
  const tan = D.analizTanim; if (!tan || !D.proje) return;
  const odak = document.activeElement?.dataset?.ek;
  $("#analizKartlar").innerHTML = Object.entries(tan).map(([tur, a]) => {
    const s = D.proje.analizler[tur] || {}, d = s.durum || "yok";
    const eksik = a.gerekir.filter(g => analizDurum(g) !== "bitti");
    const sonuc = d === "bitti" ? analizSonuc(tur) : [];
    const engel = eksik.length ? `${t("Önce")}: ${eksik.map(g => t(tan[g].ad)).join(", ")}` :
      tur === "dogrulama" && !D.proje.dogrulama_var ? t("Önce CSV yükleyin") :
      tur === "degisim" && !D.proje.etkin_parametreler?.degisim_proje ? t("Önce proje seçin") : "";
    let alt;
    if (d === "calisiyor" || d === "bekliyor") alt = `<div style="flex:1"><div class="cubuk"><i style="width:${Math.max(3, (s.ilerleme || 0) * 100)}%"></i></div>
      <small>${d === "bekliyor" ? t("Sırada") : esc(t(s.adim || ""))} · %${nf((s.ilerleme || 0) * 100)}</small></div>
      <button class="btn hayalet kucuk" data-iptal="${tur}">${t("İptal")}</button>`;
    else alt = `<button class="btn ${d === "bitti" ? "hayalet kucuk" : ""}" data-calistir="${tur}" ${engel ? "disabled" : ""}>${t(d === "bitti" ? (tur === "rapor" ? "Yeniden oluştur" : "Yeniden çalıştır") : d === "hata" ? "Tekrar dene" : "Çalıştır")}</button>
      <small>${engel ? esc(engel) : `${t("süre")} ${ANALIZ_SURE[tur] || ""}`}</small>`;
    return `<div class="analiz-kart ${d}">
      <div class="ak-ust"><div class="ak-ikon">${ANALIZ_IKON[tur] || "•"}</div><b>${esc(t(a.ad))}</b><button class="yardim-i" data-yardim="${tur}" title="${esc(t("Bu ne demek?"))}">?</button><span class="durum ${d}">${durumAd()[d] || t("Çalışmadı")}</span></div>
      <p>${esc(t(ANALIZ_ACIKLAMA[tur] || ""))}</p>
      ${sonuc.length ? `<div class="ak-sonuc">${sonuc.map(([k, v]) => `<div><span>${esc(k)}</span><b>${esc(v)}</b></div>`).join("")}</div>` : ""}
      ${d === "hata" ? `<div class="ak-mesaj">${esc(t(s.mesaj || ""))} <a href="#" data-hata-raporu>${t("Hata raporu oluştur")}</a></div>` : ""}
      ${analizEk(tur, d)}
      <div class="ak-alt">${alt}</div></div>`;
  }).join("");
  const k = $("#analizKartlar");
  $$("[data-calistir]", k).forEach(b => b.onclick = () => analizBaslat(b.dataset.calistir));
  $$("[data-iptal]", k).forEach(b => b.onclick = () => analizIptal(b.dataset.iptal));
  $$("[data-yardim]", k).forEach(b => b.onclick = () => yardimAc(b.dataset.yardim));
  $$("[data-hata-raporu]", k).forEach(b => b.onclick = e => { e.preventDefault(); hataRaporu(); });
  $$("[data-ek]", k).forEach(el => {
    const ek = el.dataset.ek;
    if (el.tagName === "SELECT") el.onchange = () => analizEkIslem(ek, el.value);
    else el.onclick = () => analizEkIslem(ek);
  });
  if (odak) $(`[data-ek="${odak}"]`, k)?.focus();
}
async function analizEkIslem(ek, deger) {
  try {
    if (ek === "sablon") { masaustu() ? (await masaustu().sablon_kaydet()) : indir("/api/dogrulama-sablonu"); }
    if (ek === "csv") {
      if (masaustu()) { const r = await masaustu().dogrulama_sec(D.pid); if (r?.hata) bildir(t(r.hata), true); else if (r) { bildir(t("Doğrulama verisi yüklendi")); durumGuncelle(); } }
      else {
        const inp = document.createElement("input"); inp.type = "file"; inp.accept = ".csv,.txt";
        inp.onchange = async () => { const fd = new FormData(); fd.append("dosya", inp.files[0]); await api(purl("dogrulama"), { method: "POST", body: fd }); bildir(t("Doğrulama verisi yüklendi")); durumGuncelle(); };
        inp.click();
      }
    }
    if (ek === "kalibre") {
      const sec = Object.fromEntries($$("[data-kal]").map(c => [c.dataset.kal, c.checked]));
      const r = await jsonGonder(purl("kalibrasyon"), sec, "POST");
      bildir(r.uygulanan.length ? t("Kalibrasyon uygulandı; analizler yeniden hesaplanıyor") : t("Uygulanacak öneri seçilmedi"));
      durumGuncelle();
    }
    if (ek === "degisim-proje") { await jsonGonder(purl("parametreler"), { degisim_proje: deger }, "PATCH"); await durumGuncelle(); }
    if (ek === "koordinat") { const r = await jsonGonder("/api/ayarlar", { koordinat: deger }); D.ayar = r.ayarlar; bildir(t("Koordinat sistemi kaydedildi")); analizKartlariCiz(); }
    if (ek === "zip" && D.veri.disari) { masaustu() ? yerelKaydet(D.veri.disari.zip) : indir(purl(`dosya/${D.veri.disari.zip}?indir=1`)); }
    if (ek === "disari-klasor") masaustu()?.klasor_ac(D.pid, "disari");
    if (ek === "pdf") raporAc(true);
    if (ek === "html") raporAc(false);
  } catch (e) { bildir(e.message, true); }
}
async function analizBaslat(tur) {
  try { D.proje = await api(purl(`analiz/${tur}`), { method: "POST" }); D.eskiDurum[tur] = "bekliyor"; durumGuncelle(); }
  catch (e) { bildir(e.message, true); }
}
async function analizIptal(tur) {
  try { await api(purl(`analiz/${tur}/iptal`), { method: "POST" }); bildir(t("İptal ediliyor…")); setTimeout(durumGuncelle, 600); }
  catch (e) { bildir(e.message, true); }
}

// ------------------------------------------------------------------ dosyalar
const KLASOR_AD = { "": "Rapor", grafikler: "Sonar görüntüleri ve grafikler", hacim: "Kot–alan–hacim ve belirsizlik", uydu: "Uydu üzerinde haritalar",
  zemin: "Zemin sınıflaması ve numune", morfoloji: "Hacim, eğim ve rota", dogrulama: "Saha doğrulaması", degisim: "Değişim analizi",
  disari: "Mühendislik çıktıları", sertnokta: "Sert nokta taraması", bitki: "Bitki örtüsü", balik: "Balık ve kabarcık" };
async function dosyalarCiz() {
  const l = await api(purl("dosyalar"));
  const gruplar = {};
  l.forEach(f => (gruplar[f.klasor] ??= []).push(f));
  const sira = ["", "disari", "grafikler", "hacim", "uydu", "zemin", "morfoloji", "dogrulama", "degisim", "sertnokta", "bitki", "balik"];
  $("#dosyaListe").innerHTML = sira.filter(k => gruplar[k]).map(k => {
    const res = gruplar[k].filter(f => f.tur === "png"), diger = gruplar[k].filter(f => f.tur !== "png");
    return `<div class="dosya-grup"><h3>${esc(t(KLASOR_AD[k] || k))}</h3>
      ${res.length ? `<div class="galeri">${res.map(f => `<div class="galeri-oge" data-yol="${esc(f.yol)}"><img loading="lazy" src="${purl("dosya/" + f.yol)}" alt=""><span>${esc(f.yol.split("/").pop())}</span></div>`).join("")}</div>` : ""}
      ${diger.length ? `<div class="indirmeler" style="margin-top:10px">${diger.map(f => `<a class="indirme" data-yol="${esc(f.yol)}" data-tur="${f.tur}" href="${purl("dosya/" + f.yol)}${["html", "pdf"].includes(f.tur) ? "" : "?indir=1"}" ${["html", "pdf"].includes(f.tur) ? 'target="_blank" rel="noopener"' : ""}><em>${f.tur}</em>${esc(f.yol.split("/").pop())}<span class="ince">${f.boyut > 1e6 ? nf(f.boyut / 1e6, 1) + " MB" : nf(f.boyut / 1024) + " KB"}</span></a>`).join("")}</div>` : ""}
    </div>`;
  }).join("") || `<p class="aciklama">${esc(t("Henüz dosya yok."))}</p>`;
  $$(".galeri-oge").forEach(g => g.onclick = () => {
    const b = $("#buyutec"), u = purl("dosya/" + g.dataset.yol);
    $("img", b).src = u; $(".buyutec-alt span", b).textContent = g.dataset.yol; $(".buyutec-alt a", b).href = u + "?indir=1";
    $(".buyutec-alt a", b).dataset.yol = g.dataset.yol; b.hidden = false;
  });
}

// ------------------------------------------------------------------ sekmeler / ust islemler
function sekmeAc(s) {
  D.sekme = s;
  $$("#sekmeler button").forEach(b => b.classList.toggle("aktif", b.dataset.sekme === s));
  $$(".sekme").forEach(x => x.hidden = x.id !== "sekme-" + s);
  if (s === "harita" && D.harita) {
    const sigdir = (deneme = 0) => {
      if (!D.harita) return;
      if ($("#harita").clientWidth < 50 && deneme < 20) { setTimeout(() => sigdir(deneme + 1), 50); return; }
      D.harita.invalidateSize();
      if (!D.haritaSigdi) {
        D.harita.fitBounds(D.veri.kb?.sinir || D.veri.ozet.sinir, { paddingTopLeft: [60, 50], paddingBottomRight: [270, 40] });
        D.haritaSigdi = true;
      }
    };
    setTimeout(sigdir, 30);
  }
  if (s !== "sonar" && D.duzenle) duzenleKapat(true);
  if (s !== "3d" && typeof uc3dDur === "function") uc3dDur();
  if (s === "3d") uc3dAc();
  if (s === "sonar") sonarKur();
  if (s === "grafik") grafikKur();
  if (s === "analiz") analizKartlariCiz();
  if (s === "dosya") dosyalarCiz();
}
async function hataRaporu() {
  try {
    if (masaustu()) { const r = await masaustu().hata_raporu_kaydet(D.pid || null); if (r?.kaydedildi) bildir(t("Hata raporu kaydedildi: ") + r.kaydedildi); }
    else indir(`/api/hata-raporu?pid=${D.pid || ""}`);
  } catch (e) { bildir(e.message, true); }
}
async function yenidenHesapla() {
  try { await api(purl("yeniden"), { method: "POST" }); bildir(t("Analizler yeniden hesaplanıyor")); durumGuncelle(); }
  catch (e) { bildir(e.message, true); }
}
function menuBagla(btn, menu, islem) {
  btn.onclick = e => { e.stopPropagation(); const ac = menu.hidden; $$(".menu").forEach(m => m.hidden = true); menu.hidden = !ac; };
  $$("button", menu).forEach(b => b.onclick = () => { menu.hidden = true; islem(b.dataset.r || b.dataset.d); });
}
document.addEventListener("click", () => $$(".menu").forEach(m => m.hidden = true));
function ustBagla() {
  $$("#sekmeler button").forEach(b => b.onclick = () => sekmeAc(b.dataset.sekme));
  $("#projeAd").onchange = async e => {
    try { await jsonGonder(`/api/projeler/${D.pid}`, { ad: e.target.value }, "PATCH"); listeYukle(); }
    catch (er) { bildir(er.message, true); }
  };
  $("#projeAd").onkeydown = e => { if (e.key === "Enter") e.target.blur(); };
  menuBagla($("#raporBtn"), $("#raporMenu"), r => {
    const d = analizDurum("rapor");
    if (r === "yeni" || d !== "bitti") {
      if (d === "calisiyor" || d === "bekliyor") { bildir(t("Rapor hazırlanıyor…")); return; }
      analizBaslat("rapor"); bildir(t("Rapor hazırlanıyor; bitince bu menüden açılır")); return;
    }
    raporAc(r === "pdf");
  });
  menuBagla($("#dahaBtn"), $("#dahaMenu"), async r => {
    if (r === "yeniden") yenidenHesapla();
    if (r === "hata") hataRaporu();
    if (r === "sil") {
      if (!confirm(`"${D.proje.ad}" ${t("projesi ve tüm çıktıları kalıcı olarak silinsin mi?")}`)) return;
      try { await api(`/api/projeler/${D.pid}`, { method: "DELETE" }); D.pid = null; katmanlariSifirla(); $("#proje").hidden = true; $("#karsilama").hidden = false; history.replaceState(null, "", "#"); listeYukle(); bildir(t("Proje silindi")); }
      catch (e) { bildir(e.message, true); }
    }
  });
  $("#yenidenBtn").onclick = yenidenHesapla;
  $("#temelIptal").onclick = () => analizIptal("temel");
  $("#kayitEkleBtn").onclick = kayitEkle;
  $("#projeAyarBtn").onclick = projeAyarlari;
  $("#kcKapat").onclick = () => { $("#kesitCekmece").hidden = true; if (D.isaret) D.harita.removeLayer(D.isaret); };
  $("#kcSonar").onclick = () => sekmeAc("sonar");
  $("#pfKapat").onclick = () => { $("#profilCekmece").hidden = true; };
  $("#pfCsv").onclick = profilCsv;
  $$("#aracCubugu button").forEach(b => b.onclick = e => { e.stopPropagation(); aracSec(b.dataset.arac); });
  $("#projeAra").oninput = listeCiz;
  $("#ayarlarBtn").onclick = ayarlarAc;
  $("#yardimBtn").onclick = () => yardimAc();
  $("#hakkindaBtn").onclick = hakkindaAc;
  $$(".yardim-i[data-yardim]").forEach(b => b.onclick = () => yardimAc(b.dataset.yardim));
  const bu = $("#buyutec");
  bu.onclick = e => { if (e.target === bu || e.target.classList.contains("kapat")) bu.hidden = true; };
  addEventListener("keydown", e => { if (e.key === "Escape") bu.hidden = true; });
}
document.addEventListener("click", e => {
  const a = e.target.closest(".indirme, .buyutec-alt a");
  if (!a || !masaustu()) return;
  e.preventDefault();
  if (a.dataset.tur === "html") raporAc(false);
  else if (a.dataset.tur === "pdf") masaustu().ac(D.pid, a.dataset.yol);
  else yerelKaydet(a.dataset.yol);
});

// ------------------------------------------------------------------ ayarlar
function secim(ad, deger, secenekler) {
  return `<select name="${ad}">${secenekler.map(([v, e]) => `<option value="${esc(v)}" ${String(deger) === String(v) ? "selected" : ""}>${esc(t(e))}</option>`).join("")}</select>`;
}
const yardimDugme = k => `<button type="button" class="yardim-i" data-yardim="${k}">?</button>`;
async function ayarlarAc() {
  const m = await api("/api/ayarlar");
  D.ayarMeta = m; D.ayar = m.ayarlar;
  const a = m.ayarlar;
  const p = pencereAc({
    baslik: t("Ayarlar"), genis: true,
    govde: `<form class="form ayar-form" id="ayarForm">
      <fieldset><legend>${t("Genel")}</legend>
        <label>${t("Dil")}${secim("dil", a.dil, [["tr", "Türkçe"], ["en", "English"]])}</label>
        <label>${t("Uzunluk birimi")}${secim("birim", a.birim, [["m", "Metre (m)"], ["ft", "Fit (ft)"]])}</label>
        <label class="onay"><input type="checkbox" name="guncelleme_denetle" ${a.guncelleme_denetle ? "checked" : ""}> ${t("Açılışta güncellemeleri denetle")}</label>
        <label class="onay"><input type="checkbox" id="acilisSec" ${(() => { try { return localStorage.getItem("acilis_kapali") !== "1"; } catch { return true; } })() ? "checked" : ""}> ${t("Açılış animasyonunu göster")}</label>
      </fieldset>
      <fieldset><legend>${t("Harita")}</legend>
        <label>${t("Kontur aralığı")} ${yardimDugme("kontur")}${secim("kontur_araligi", a.kontur_araligi, [[0, "Otomatik"], [0.1, "0,1 m"], [0.25, "0,25 m"], [0.5, "0,5 m"], [1, "1 m"], [2, "2 m"], [5, "5 m"]])}</label>
        <label>${t("Derinlik renk paleti")}<div class="palet-sec">${m.paletler.map(pl => `<label class="palet ${a.renk_paleti === pl ? "aktif" : ""}"><input type="radio" name="renk_paleti" value="${pl}" ${a.renk_paleti === pl ? "checked" : ""}><i style="background:${PALET_CSS[pl] || "#444"}"></i><span>${PALET_AD[pl] || pl}</span></label>`).join("")}</div></label>
      </fieldset>
      <fieldset><legend>${t("Mühendislik çıktıları")}</legend>
        <label>${t("Koordinat sistemi")} ${yardimDugme("koordinat")}${secim("koordinat", a.koordinat, Object.entries(m.koordinatlar))}</label>
      </fieldset>
      <fieldset><legend>${t("Yeni projeler için ölçüm varsayılanları")}</legend>
        <label>${t("Ses hızı düzeltmesi")} ${yardimDugme("ses_hizi")}${secim("ses_hizi_modu", a.ses_hizi_modu, [["kapali", "Kapalı"], ["sicaklik", "Su sıcaklığından hesapla"], ["elle", "Elle gir"]])}</label>
        <label>${t("Cihazın varsaydığı ses hızı (m/s)")}<input name="cihaz_ses_hizi" type="number" step="1" value="${a.cihaz_ses_hizi}"></label>
        <label>${t("Elle ses hızı (m/s)")}<input name="ses_hizi_elle" type="number" step="1" value="${a.ses_hizi_elle}"></label>
        <label>${t("Batma payı (m)")} ${yardimDugme("batma_payi")}<input name="batma_payi" type="number" step="0.01" value="${a.batma_payi}"></label>
      </fieldset>
      <fieldset class="tam"><legend>${t("Rapor")}</legend>
        <div class="iki">
          <label>${t("Firma / kurum adı")}<input name="firma_adi" maxlength="160" value="${esc(a.firma_adi || "")}"></label>
          <label>${t("Hazırlayan")}<input name="hazirlayan" maxlength="160" value="${esc(a.hazirlayan || "")}"></label>
        </div>
        <div class="logo-alan"><div class="logo-onizleme" id="logoOnizleme">${m.logo_var ? `<img src="/api/ayarlar/logo?t=${Date.now()}" alt="">` : `<span class="ince">${t("Logo yok")}</span>`}</div>
          <button type="button" class="btn hayalet kucuk" id="logoSecBtn">${t("Firma logosu seç")}</button>
          <button type="button" class="btn hayalet kucuk" id="logoSilBtn" ${m.logo_var ? "" : "hidden"}>${t("Kaldır")}</button></div>
      </fieldset>
    </form>`,
    alt: `<span class="ince">${t("Harita ve ölçüm ayarları, analizler yeniden hesaplanınca uygulanır.")}</span><button class="btn hayalet" data-iptal>${t("Vazgeç")}</button><button class="btn" data-kaydet>${t("Kaydet")}</button>`,
  });
  $$(".yardim-i", p).forEach(b => b.onclick = () => yardimAc(b.dataset.yardim, true));
  $$(".palet input", p).forEach(r => r.onchange = () => $$(".palet", p).forEach(l => l.classList.toggle("aktif", $("input", l).checked)));
  $("#logoSecBtn").onclick = async () => {
    let r;
    if (masaustu()) r = await masaustu().logo_sec();
    else r = await new Promise(res => { const i = document.createElement("input"); i.type = "file"; i.accept = "image/*"; i.onchange = async () => { const fd = new FormData(); fd.append("dosya", i.files[0]); try { res(await api("/api/ayarlar/logo", { method: "POST", body: fd })); } catch (e) { res({ hata: e.message }); } }; i.click(); });
    if (r?.hata) { bildir(t(r.hata), true); return; }
    if (r) { $("#logoOnizleme").innerHTML = `<img src="/api/ayarlar/logo?t=${Date.now()}" alt="">`; $("#logoSilBtn").hidden = false; }
  };
  $("#logoSilBtn").onclick = async () => { await api("/api/ayarlar/logo", { method: "DELETE" }); $("#logoOnizleme").innerHTML = `<span class="ince">${t("Logo yok")}</span>`; $("#logoSilBtn").hidden = true; };
  $("[data-iptal]", p).onclick = pencereKapat;
  $("[data-kaydet]", p).onclick = async () => {
    const f = $("#ayarForm"), fd = new FormData(f), yeni = {};
    for (const [k, v] of fd.entries()) yeni[k] = v;
    yeni.guncelleme_denetle = $("[name=guncelleme_denetle]", f).checked;
    try { localStorage.setItem("acilis_kapali", $("#acilisSec").checked ? "0" : "1"); } catch { /* yok */ }
    ["kontur_araligi", "cihaz_ses_hizi", "ses_hizi_elle", "batma_payi"].forEach(k => yeni[k] = parseFloat(String(yeni[k]).replace(",", ".")));
    try {
      const eski = D.ayar;
      const r = await jsonGonder("/api/ayarlar", yeni);
      D.ayar = r.ayarlar;
      pencereKapat();
      if (eski.dil !== D.ayar.dil) { location.reload(); return; }
      const haritaDegisti = eski.kontur_araligi !== D.ayar.kontur_araligi || eski.renk_paleti !== D.ayar.renk_paleti;
      if (eski.birim !== D.ayar.birim && D.pid) { D.grafikHazir = false; katmanlariSifirla(); await temelYukle(); for (const tur of ["zemin", "uydu", "taramalar", "degisim"]) if (analizDurum(tur) === "bitti") await ekVeriYukle(tur); katmanlariKur(); sekmeAc(D.sekme); }
      if (D.pid) { ustBilgi(); analizKartlariCiz(); listeCiz(); }
      bildir(haritaDegisti && D.pid ? t("Ayarlar kaydedildi. Haritaların yeni ayarlarla çizilmesi için 'Yeniden hesapla'yı kullanın.") : t("Ayarlar kaydedildi"));
    } catch (e) { bildir(e.message, true); }
  };
}
const PALET_CSS = {
  viridis_r: "linear-gradient(90deg,#fde725,#5ec962,#21918c,#3b528b,#440154)", Blues: "linear-gradient(90deg,#f7fbff,#9ecae1,#4292c6,#08306b)",
  ocean_r: "linear-gradient(90deg,#ffffff,#56a0c0,#0f5a8c,#000a4d,#007a00)", cividis_r: "linear-gradient(90deg,#fee838,#a59c74,#575c6d,#00224e)",
  plasma_r: "linear-gradient(90deg,#f0f921,#f89540,#cc4778,#7e03a8,#0d0887)", YlGnBu: "linear-gradient(90deg,#ffffd9,#7fcdbb,#1d91c0,#081d58)",
  turbo_r: "linear-gradient(90deg,#7a0403,#fb8022,#a4fc3c,#28bbec,#30123b)", terrain_r: "linear-gradient(90deg,#ffffff,#a68b5b,#ffff99,#00a65d,#333399)",
};
const PALET_AD = { viridis_r: "Viridis", Blues: "Mavi", ocean_r: "Okyanus", cividis_r: "Cividis", plasma_r: "Plazma", YlGnBu: "Sarı-mavi", turbo_r: "Turbo", terrain_r: "Arazi" };

// ------------------------------------------------------------------ proje ayarlari
async function projeAyarlari() {
  if (!D.proje) return;
  const p0 = D.proje, ep = p0.etkin_parametreler || {}, pp = p0.parametreler || {};
  const kayitlar = (p0.kayitlar || []).map(k => `<li><b>${esc(k.ad)}</b><span class="ince">${nf(k.boyut / 1e6, 1)} MB</span>
      ${(p0.kayitlar || []).length > 1 ? `<button type="button" class="btn hayalet kucuk tehlike" data-cikar="${esc(k.dosya)}">${t("Çıkar")}</button>` : ""}</li>`).join("");
  const p = pencereAc({
    baslik: t("Proje ayarları"), genis: true,
    govde: `<form class="form ayar-form" id="pAyarForm">
      <fieldset><legend>${t("Kayıtlar")}</legend>
        <ul class="kayit-liste">${kayitlar}</ul>
        <button type="button" class="btn hayalet kucuk" id="pKayitEkle">+ ${t("Kayıt ekle")}</button>
        <small class="ince">${t("Aynı göletin birden çok RSD dosyası tek haritada birleştirilir. Kayıt eklenince elle düzeltmeler sıfırlanır.")}</small>
      </fieldset>
      <fieldset><legend>${t("Ölçüm parametreleri")}</legend>
        <label>${t("Ses hızı düzeltmesi")} ${yardimDugme("ses_hizi")}${secim("ses_hizi_modu", ep.ses_hizi_modu, [["kapali", "Kapalı"], ["sicaklik", "Su sıcaklığından hesapla"], ["elle", "Elle gir"]])}</label>
        <label>${t("Cihazın varsaydığı ses hızı (m/s)")}<input name="cihaz_ses_hizi" type="number" step="1" value="${ep.cihaz_ses_hizi}"></label>
        <label>${t("Elle ses hızı (m/s)")}<input name="ses_hizi_elle" type="number" step="1" value="${ep.ses_hizi_elle}"></label>
        <label>${t("Batma payı (m)")} ${yardimDugme("batma_payi")}<input name="batma_payi" type="number" step="0.01" value="${ep.batma_payi}"></label>
        <label>${t("Su yüzeyi kotu (m)")} ${yardimDugme("su_kotu")}<input name="su_kotu" type="number" step="0.001" value="${pp.su_kotu ?? 0}"></label>
      </fieldset>
    </form>`,
    alt: `<span class="ince">${t("Değişiklikten sonra 'Yeniden hesapla' gerekir.")}</span><button class="btn hayalet" data-iptal>${t("Vazgeç")}</button><button class="btn" data-kaydet>${t("Kaydet")}</button>`,
  });
  $$(".yardim-i", p).forEach(b => b.onclick = () => yardimAc(b.dataset.yardim, true));
  $("#pKayitEkle").onclick = () => { pencereKapat(); kayitEkle(); };
  $$("[data-cikar]", p).forEach(b => b.onclick = async () => {
    if (!confirm(t("Bu kayıt projeden çıkarılsın mı? Analizler yeniden hesaplanır."))) return;
    try { await api(purl(`kayitlar/${encodeURIComponent(b.dataset.cikar)}`), { method: "DELETE" }); pencereKapat(); bildir(t("Kayıt çıkarıldı")); durumGuncelle(true); }
    catch (e) { bildir(e.message, true); }
  });
  $("[data-iptal]", p).onclick = pencereKapat;
  $("[data-kaydet]", p).onclick = async () => {
    const fd = new FormData($("#pAyarForm")), yeni = {};
    for (const [k, v] of fd.entries()) yeni[k] = k === "ses_hizi_modu" ? v : parseFloat(String(v).replace(",", "."));
    try { await jsonGonder(purl("parametreler"), yeni, "PATCH"); pencereKapat(); bildir(t("Proje ayarları kaydedildi")); durumGuncelle(); }
    catch (e) { bildir(e.message, true); }
  };
}

// ------------------------------------------------------------------ hakkinda / guncelleme
async function hakkindaAc() {
  const h = await api("/api/hakkinda");
  const g = D.guncel;
  const p = pencereAc({
    baslik: t("Hakkında"), genis: true,
    govde: `<div class="hakkinda">
      <div class="hk-bant"><img src="/static/logo_yatay.png" alt="BAHR SONARVIEW"></div>
      <div class="hk-satir"><div><span class="ince">${t("Sürüm")}</span><b>${esc(h.surum)}</b></div>
        <div><span class="ince">${t("Telif")}</span><b>${esc(h.telif)}</b></div>
        <div><span class="ince">${t("Web")}</span><a href="#" data-dis="${esc(h.web)}">${esc(h.web.replace("https://", ""))}</a></div></div>
      <p class="hk-lisans"><b>${t("Lisans")}:</b> ${esc(t(h.lisans))}</p>
      <div class="hk-guncel" id="hkGuncel">${g?.yeni_var ? `<b>${t("Yeni sürüm hazır")}: v${esc(g.son)}</b> <button class="btn kucuk" data-guncel>${t("Ayrıntılar")}</button>` :
        `<span class="ince">${g?.hata ? esc(t(g.hata)) : g ? t("Program güncel.") : ""}</span> <button class="btn hayalet kucuk" data-denetle>${t("Güncellemeleri denetle")}</button>`}</div>
      <h3>${t("Kullanılan açık kaynak bileşenler")}</h3>
      <div class="hk-tablo"><table><tr><th>${t("Bileşen")}</th><th>${t("Sürüm")}</th><th>${t("Lisans")}</th></tr>
        ${h.kutuphaneler.map(k => `<tr><td>${esc(t(k.ad))}</td><td>${esc(k.surum || "")}</td><td>${esc(t(k.lisans || ""))}</td></tr>`).join("")}</table></div>
      <p class="ince">Python ${esc(h.python)} · ${esc(h.windows)}<br>${t("Veri klasörü")}: <code>${esc(h.veri_klasoru)}</code></p>
    </div>`,
    alt: `<button class="btn hayalet" data-hata>${t("Hata raporu oluştur")}</button><button class="btn" data-tamam>${t("Kapat")}</button>`,
  });
  $$("[data-dis]", p).forEach(a => a.onclick = e => { e.preventDefault(); masaustu() ? masaustu().disari_ac(a.dataset.dis) : window.open(a.dataset.dis, "_blank", "noopener"); });
  $("[data-tamam]", p).onclick = pencereKapat;
  $("[data-hata]", p).onclick = hataRaporu;
  $("[data-guncel]", p)?.addEventListener("click", guncellemePenceresi);
  $("[data-denetle]", p)?.addEventListener("click", async () => { await guncellemeDenetle(true); hakkindaAc(); });
}
async function guncellemeDenetle(zorla = false) {
  try { D.guncel = await api(`/api/guncelleme?zorla=${zorla ? 1 : 0}`); } catch (e) { D.guncel = { hata: e.message }; }
  const g = D.guncel;
  $("#guncelRozet").hidden = !g?.yeni_var;
  if (g?.yeni_var) {
    const b = $("#guncelBant");
    b.innerHTML = `<span><b>BAHR SONARVIEW v${esc(g.son)}</b> ${esc(t("hazır"))} (${esc(t("kullandığınız"))}: v${esc(g.mevcut)}).</span><button class="btn kucuk" id="guncelDetay">${esc(t("Ayrıntılar"))}</button><button class="kapat" id="guncelGizle" aria-label="Kapat">×</button>`;
    b.hidden = false;
    $("#guncelDetay").onclick = guncellemePenceresi;
    $("#guncelGizle").onclick = () => { b.hidden = true; };
  }
  return g;
}
function guncellemePenceresi() {
  const g = D.guncel; if (!g) return;
  const p = pencereAc({
    baslik: `${t("Güncelleme")}: v${g.son}`,
    govde: `<div class="guncel-govde"><p>${t("Kullandığınız sürüm")}: <b>v${esc(g.mevcut)}</b> · ${t("Yeni sürüm")}: <b>v${esc(g.son)}</b>${g.tarih ? ` (${esc(g.tarih)})` : ""}${g.boyut ? ` · ${nf(g.boyut / 1e6, 0)} MB` : ""}</p>
      <pre class="notlar">${esc(g.notlar || t("Sürüm notu yok."))}</pre>
      <div id="gIlerleme" hidden><div class="cubuk buyuk"><i id="gCubuk"></i></div><small id="gYazi" class="ince"></small></div>
      <p class="ince">${t("Projeleriniz ve ayarlarınız güncellemeden etkilenmez.")}</p></div>`,
    alt: g.kurulabilir ? `<button class="btn hayalet" data-sayfa>${t("Sürüm sayfası")}</button><button class="btn" data-kur>${t("İndir ve kur")}</button>` :
      `<button class="btn hayalet" data-iptal>${t("Kapat")}</button><button class="btn" data-sayfa>${t("İndirme sayfasını aç")}</button>`,
  });
  const sayfa = () => masaustu() ? masaustu().disari_ac(g.sayfa) : window.open(g.sayfa, "_blank", "noopener");
  $("[data-sayfa]", p).onclick = sayfa;
  $("[data-iptal]", p)?.addEventListener("click", pencereKapat);
  $("[data-kur]", p)?.addEventListener("click", async e => {
    const b = e.currentTarget; b.disabled = true;
    try {
      await api("/api/guncelleme/indir", { method: "POST" });
      $("#gIlerleme").hidden = false;
      for (;;) {
        const s = await api("/api/guncelleme/durum");
        $("#gCubuk").style.width = (s.yuzde || 2) + "%"; $("#gYazi").textContent = `${t("İndiriliyor")} %${nf(s.yuzde)}`;
        if (s.durum === "hazir") break;
        if (s.durum === "hata") throw new Error(t(s.hata));
        await new Promise(r => setTimeout(r, 700));
      }
      if (calisiyorMu() && !confirm(t("Çalışan analizler durdurulacak. Program kapanıp güncellenerek yeniden açılsın mı?"))) { b.disabled = false; return; }
      $("#gYazi").textContent = t("Kuruluyor; program kapanıp yeniden açılacak…");
      await api("/api/guncelleme/kur", { method: "POST" });
      masaustu()?.uygulamayi_kapat();
    } catch (er) { bildir(er.message, true); b.disabled = false; }
  });
}

// ------------------------------------------------------------------ yardim
function yardimAc(konu, ustune = false) {
  const Y = window.YARDIM || {};
  const dil = window.DIL === "en" ? "en" : "tr";
  const konular = Object.entries(Y);
  const onceki = ustune ? { baslik: $("#pencereBaslik").textContent, govde: $("#pencereGovde").innerHTML, alt: $("#pencereAlt").innerHTML } : null;
  const ciz = k => {
    const y = Y[k]?.[dil] || Y[k]?.tr;
    $("#yardimIcerik").innerHTML = y ? `<h3>${esc(y.baslik)}</h3>${y.metin}` : "";
    $$("#yardimListe button").forEach(b => b.classList.toggle("aktif", b.dataset.k === k));
  };
  if (ustune) {                                              // ayar penceresinin icinden: kisa aciklama kutusu
    const y = Y[konu]?.[dil] || Y[konu]?.tr; if (!y) return;
    const kutu = document.createElement("div");
    kutu.className = "yardim-kutu";
    kutu.innerHTML = `<div><b>${esc(y.baslik)}</b>${y.metin}<button class="btn kucuk">${esc(t("Tamam"))}</button></div>`;
    $(".pencere").append(kutu);
    $("button", kutu).onclick = () => kutu.remove();
    return onceki;
  }
  pencereAc({
    baslik: t("Yardım"), genis: true,
    govde: `<div class="yardim"><div class="yardim-sol"><input type="search" id="yardimAra" placeholder="${esc(t("Konu ara…"))}"><nav id="yardimListe">${konular.map(([k, v]) => `<button data-k="${k}" data-grup="${v.grup || ""}">${esc((v[dil] || v.tr).baslik)}</button>`).join("")}</nav></div>
      <article id="yardimIcerik" class="yardim-icerik"></article></div>`,
    alt: `<span class="ince">${t("Klavye")}: ←/→ ${t("sonarda ilerle")} · ${t("boşluk")}: ${t("oynat")} · Ctrl+Z: ${t("düzeltmeyi geri al")} · Esc: ${t("kapat")}</span><button class="btn" data-tamam>${t("Kapat")}</button>`,
  });
  $$("#yardimListe button").forEach(b => b.onclick = () => ciz(b.dataset.k));
  $("#yardimAra").oninput = e => { const q = e.target.value.toLocaleLowerCase(yerel()); $$("#yardimListe button").forEach(b => { const y = Y[b.dataset.k]; b.hidden = q && !((y[dil] || y.tr).baslik + (y[dil] || y.tr).metin).toLocaleLowerCase(yerel()).includes(q); }); };
  $("[data-tamam]").onclick = pencereKapat;
  ciz(konu && Y[konu] ? konu : konular[0]?.[0]);
}

// ------------------------------------------------------------------ baslangic
(async function () {
  try { const m = await api("/api/ayarlar"); D.ayarMeta = m; D.ayar = m.ayarlar; window.DIL = D.ayar.dil; } catch { window.DIL = "tr"; }
  document.documentElement.lang = window.DIL;
  dilUygula(document.body);
  yuklemeBagla(); ustBagla(); sonarBagla(); masaustuHazir(); ucBagla();
  $("#klasorBtn").onclick = () => masaustu()?.klasor_ac(D.pid);
  try { D.analizTanim = await api("/api/analizler"); } catch (e) { bildir(t("Sunucuya bağlanılamadı"), true); }
  await listeYukle();
  const h = location.hash.slice(1);
  if (h && D.projeler.some(p => p.id === h)) projeAc(h);
  if (D.ayar?.guncelleme_denetle !== false) setTimeout(() => guncellemeDenetle(false), 2500);
})();
