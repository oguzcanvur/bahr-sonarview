/* SonarLab arayuzu */
"use strict";

const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const nf = (v, d = 0) => v == null || Number.isNaN(v) ? "–" :
  new Intl.NumberFormat("tr-TR", { minimumFractionDigits: d, maximumFractionDigits: d }).format(v);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const D = {
  projeler: [], pid: null, proje: null, analizTanim: null,
  veri: {}, harita: null, altliklar: {}, katmanlar: {}, acikKatman: new Set(["rota", "batimetri", "kontur"]),
  grafikler: [], sonarSatir: 0, oynuyor: false, sekme: "harita", eskiDurum: {}, kesitIstek: 0, isaret: null,
};

// ------------------------------------------------------------------ yardimcilar
async function api(url, opt = {}) {
  const r = await fetch(url, opt);
  if (!r.ok) {
    let m = r.statusText;
    try { m = (await r.json()).detail || m; } catch { /* yok */ }
    throw new Error(m);
  }
  return r.headers.get("content-type")?.includes("json") ? r.json() : r;
}
function bildir(m, hata = false) {
  const b = $("#bildirim");
  b.textContent = m; b.className = "bildirim" + (hata ? " hata" : ""); b.hidden = false;
  clearTimeout(bildir.t); bildir.t = setTimeout(() => b.hidden = true, hata ? 6000 : 3500);
}
const purl = (yol) => `/api/projeler/${D.pid}/${yol}`;
const durumAd = { bekliyor: "Sırada", calisiyor: "Çalışıyor", bitti: "Tamamlandı", hata: "Hata" };
function analizDurum(t) { return D.proje?.analizler?.[t]?.durum; }
function sureYaz(dk) { const m = Math.floor(dk), s = Math.round((dk - m) * 60); return `${m}:${String(s).padStart(2, "0")}`; }

// ------------------------------------------------------------------ proje listesi
async function listeYukle() {
  D.projeler = await api("/api/projeler");
  const el = $("#projeListe");
  if (!D.projeler.length) { el.innerHTML = `<div class="bos-liste">Henüz proje yok. İlk kaydını yükle.</div>`; return; }
  el.innerHTML = D.projeler.map(p => {
    const ds = Object.values(p.analizler || {}).map(a => a.durum);
    const d = ds.includes("hata") ? "hata" : ds.some(x => x === "calisiyor" || x === "bekliyor") ? "calisiyor" : "bitti";
    const oz = p.ozet;
    const alt = oz ? `${oz.tarih} · ${nf(oz.derinlik_min, 1)}–${nf(oz.derinlik_max, 1)} m · ${nf(oz.sure_dk)} dk` :
      new Date(p.olusturma * 1000).toLocaleString("tr-TR");
    return `<button class="proje-oge ${p.id === D.pid ? "aktif" : ""}" data-id="${p.id}">
      <b>${esc(p.ad)}</b><span class="nokta ${d}" title="${durumAd[d]}"></span><small>${esc(alt)}</small></button>`;
  }).join("");
  $$(".proje-oge", el).forEach(b => b.onclick = () => projeAc(b.dataset.id));
}

// ------------------------------------------------------------------ yukleme
function dosyaYukle(f) {
  if (!f) return;
  if (!/\.rsd$/i.test(f.name)) { bildir("Yalnızca Garmin .RSD dosyaları destekleniyor", true); return; }
  const fd = new FormData();
  fd.append("dosya", f); fd.append("ad", f.name.replace(/\.rsd$/i, ""));
  const x = new XMLHttpRequest();
  $("#yuklemeDurum").hidden = false; $("#yuklemeAd").textContent = f.name;
  x.upload.onprogress = e => {
    if (!e.lengthComputable) return;
    const y = e.loaded / e.total * 100;
    $("#yuklemeYuzde").textContent = y < 100 ? `%${nf(y)}` : "kaydediliyor…";
    $("#yuklemeCubuk").style.width = y + "%";
  };
  x.onload = async () => {
    $("#yuklemeDurum").hidden = true;
    if (x.status >= 300) { let m = "Yükleme başarısız"; try { m = JSON.parse(x.responseText).detail; } catch { } bildir(m, true); return; }
    const p = JSON.parse(x.responseText);
    await listeYukle(); projeAc(p.id);
  };
  x.onerror = () => { $("#yuklemeDurum").hidden = true; bildir("Yükleme sırasında bağlantı koptu", true); };
  x.open("POST", "/api/projeler"); x.send(fd);
}
function yuklemeBagla() {
  const sec = $("#dosyaSec");
  sec.onchange = () => { dosyaYukle(sec.files[0]); sec.value = ""; };
  for (const el of [$("#yukleKart"), $("#buyukYukle")]) {
    el.onclick = e => { e.preventDefault(); sec.click(); };
    el.onkeydown = e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); sec.click(); } };
  }
  let say = 0;
  addEventListener("dragenter", e => { if (e.dataTransfer?.types?.includes("Files")) { say++; $("#birak").hidden = false; } });
  addEventListener("dragleave", () => { if (--say <= 0) { say = 0; $("#birak").hidden = true; } });
  addEventListener("dragover", e => e.preventDefault());
  addEventListener("drop", e => { e.preventDefault(); say = 0; $("#birak").hidden = true; dosyaYukle(e.dataTransfer.files[0]); });
}

// ------------------------------------------------------------------ proje acma / durum
async function projeAc(pid) {
  if (D.pid !== pid) { katmanlariSifirla(); D.veri = {}; D.eskiDurum = {}; D.sonarSatir = 0; D.oynuyor = false; }
  D.pid = pid;
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
  $("#isleniyor").hidden = temel.durum === "bitti" || temel.durum === "hata";
  $("#hataKutu").hidden = temel.durum !== "hata";
  if (temel.durum === "hata") $("#hataKutu").innerHTML = `<b>Analiz tamamlanamadı.</b> ${esc(temel.mesaj || "")}`;
  if (temel.durum !== "bitti") isleniyorCiz(temel);
  $("#sekmeler").hidden = temel.durum !== "bitti";
  if (temel.durum === "bitti") {
    if (ilk || onceki.temel !== "bitti") {
      try { await temelYukle(); } catch (e) { bildir("Harita verisi yüklenemedi: " + e.message, true); }
      if (ilk) sekmeAc(D.sekme);
    }
    // yeni biten analizler -> katmanlari yenile
    for (const [t, d] of Object.entries(simdi)) {
      if (d === "bitti" && onceki[t] && onceki[t] !== "bitti" && t !== "temel") {
        bildir(`${D.analizTanim?.[t]?.ad || t} tamamlandı`);
        await ekVeriYukle(t);
        if (D.sekme === "dosya") dosyalarCiz();
        if (t === "rapor") bildir("Rapor hazır — üstteki Rapor düğmesiyle aç");
      }
      if (d === "hata" && onceki[t] && onceki[t] !== "hata") bildir(`${D.analizTanim?.[t]?.ad || t}: hata`, true);
    }
    if (ilk) for (const t of ["zemin", "uydu", "taramalar"]) if (simdi[t] === "bitti") await ekVeriYukle(t);
  }
  analizKartlariCiz();
  const calisan = Object.values(simdi).some(d => d === "bekliyor" || d === "calisiyor");
  $("#analizRozet").hidden = !calisan; $("#analizRozet").textContent = "●";
  clearTimeout(durumGuncelle.t);
  if (calisan) durumGuncelle.t = setTimeout(() => durumGuncelle(), 1500);
  if (ilk || JSON.stringify(onceki) !== JSON.stringify(simdi)) listeYukle();
}

function isleniyorCiz(a) {
  const adimlar = D.analizTanim?.temel?.adimlar || [];
  const y = (a.ilerleme || 0) * 100;
  $("#isleniyorCubuk").style.width = Math.max(3, y) + "%";
  $("#isleniyorAdim").textContent = a.durum === "bekliyor" ? `Sırada bekliyor${D.proje.kuyruk ? ` (${D.proje.kuyruk} iş önde)` : ""}…` :
    `${a.adim || "Hazırlanıyor"} · %${nf(y)}`;
  const i = adimlar.indexOf(a.adim);
  $("#isleniyorAdimlar").innerHTML = adimlar.map((s, j) => `<li class="${j < i ? "tamam" : j === i ? "su-an" : ""}">${esc(s)}</li>`).join("");
}

function ustBilgi() {
  const oz = D.veri.ozet || D.proje.ozet;
  const p = D.proje;
  const cip = [];
  if (oz) cip.push(`${oz.tarih} · ${oz.baslangic}–${oz.bitis}`, `${nf(oz.ping)} ping`, oz.kanal.split(" (")[0], `${nf(oz.dosya_mb, 1)} MB`);
  else cip.push(esc(p.dosya_adi), `${nf(p.boyut / 1e6, 1)} MB`);
  $("#projeMeta").innerHTML = cip.map(c => `<span class="cip">${esc(c)}</span>`).join("");
  const k = $("#kpiler");
  if (!oz) { k.innerHTML = ""; return; }
  const h = D.veri.hacim;
  const kpi = [
    ["Derinlik", `${nf(oz.derinlik_min, 1)}–${nf(oz.derinlik_max, 1)}`, "m"],
    ["Ortanca derinlik", nf(oz.derinlik_medyan, 2), "m"],
    ["Haritalanan alan", nf(oz.haritalanan_alan_m2), "m²"],
    h ? ["Tahmini hacim", `${nf(h.tum_golet_hacmi_m3_kiyi0m / 1000, 1)}–${nf(h["tum_golet_hacmi_m3_kiyi0.5m"] / 1000, 1)}`, "bin m³"] :
      ["Kat edilen yol", nf(oz.yol_m), "m"],
    ["Kayıt süresi", nf(oz.sure_dk), "dk"],
    ["Su sıcaklığı", `${nf(oz.sicaklik_min, 1)}–${nf(oz.sicaklik_max, 1)}`, "°C"],
  ];
  k.innerHTML = kpi.map(([a, b, c]) => `<div class="kpi"><span>${a}</span><b>${b}</b><small>${c}</small></div>`).join("");
}

// ------------------------------------------------------------------ veri yukleme
async function webJson(ad) {
  const r = await fetch(purl("web/" + ad) + "?t=" + Date.now());
  if (!r.ok) throw new Error(`${ad} alınamadı`);
  return r.json();                       // .geojson dahil hepsi JSON
}

async function temelYukle() {
  const [ozet, rota, zaman, kb, kontur, renk] = await Promise.all(
    ["ozet.json", "rota.json", "zaman.json", "katman_batimetri.json", "kontur.geojson", "renk_viridis_r.json"].map(webJson));
  Object.assign(D.veri, { ozet, rota, zaman, kb, kontur, renk });
  ustBilgi();
  haritaKur();
  katmanlariKur();
  $("#zamanCubuk").max = ozet.toplam_satir - 1;
  $("#zcSon").textContent = `${nf(ozet.sure_dk, 1)} dk`;
  if (!D.sonarSatir) D.sonarSatir = rota.satir[Math.floor(rota.satir.length / 2)];
  D.grafikHazir = false;
}

async function ekVeriYukle(t) {
  try {
    if (t === "zemin") {
      const [kz, ks, kp, num] = await Promise.all(["katman_zemin.json", "katman_sertlik.json", "katman_penetrasyon.json", "numune.geojson"].map(webJson));
      Object.assign(D.veri, { kz, ks, kp, num });
      D.acikKatman.add("numune");
    } else if (t === "uydu") {
      const [hacim, ktg, yr] = await Promise.all(["hacim.json", "katman_tum_golet.json", "yeni_rota.json"].map(webJson));
      Object.assign(D.veri, { hacim, ktg, yr });
      try { D.veri.kiyi = await webJson("kiyi.json"); } catch { /* opsiyonel */ }
      ustBilgi();
    } else if (t === "taramalar") {
      D.veri.tar = await webJson("taramalar.json");
      try { D.veri.balik = await webJson("balik.geojson"); } catch { }
      try { D.veri.sert = await webJson("sertnokta.geojson"); } catch { }
    }
  } catch (e) { console.warn(t, e); }
  try { if (D.harita) katmanlariKur(); } catch (e) { console.warn("katman", e); }
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
  L.control.scale({ imperial: false, position: "bottomright" }).addTo(m);
  $$("#altlikSec button").forEach(b => b.onclick = () => {
    $$("#altlikSec button").forEach(x => x.classList.toggle("aktif", x === b));
    Object.values(D.altliklar).forEach(l => m.removeLayer(l));
    if (D.altliklar[b.dataset.a]) D.altliklar[b.dataset.a].addTo(m);
  });
  m.on("click", e => haritaTik(e.latlng));
  m.once("click", () => $("#haritaIpucu").style.opacity = 0);
  const s = D.veri.ozet.sinir;
  m.fitBounds(s, { padding: [40, 40] });
}

function renkSkala(v, min, max) {
  const r = D.veri.renk;
  const x = Math.max(0, Math.min(1, (v - min) / (max - min || 1))) * (r.length - 1);
  return r[Math.round(x)];
}

const KATMANLAR = [
  { id: "rota", ad: "Tekne rotası", gerekir: "temel", yap: rotaKatmani, efsane: "derinlik" },
  { id: "batimetri", ad: "Derinlik haritası", gerekir: "temel", yap: () => resimKatmani(D.veri.kb), efsane: "derinlik" },
  { id: "kontur", ad: "Eş derinlik çizgileri", gerekir: "temel", yap: konturKatmani },
  { id: "tum_golet", ad: "Tüm su alanı (tahmin)", gerekir: "uydu", veri: "ktg", yap: () => resimKatmani(D.veri.ktg), efsane: "tum" },
  { id: "kiyi", ad: "Kıyı çizgisi", gerekir: "uydu", veri: "kiyi", yap: kiyiKatmani },
  { id: "yeni_rota", ad: "Önerilen yeni rota", gerekir: "uydu", veri: "yr", yap: yeniRotaKatmani },
  { id: "zemin", ad: "Zemin sınıfları", gerekir: "zemin", veri: "kz", yap: () => resimKatmani(D.veri.kz), efsane: "zemin" },
  { id: "sertlik", ad: "Dip sertliği", gerekir: "zemin", veri: "ks", yap: () => resimKatmani(D.veri.ks), efsane: "sertlik" },
  { id: "penetrasyon", ad: "Penetrasyon", gerekir: "zemin", veri: "kp", yap: () => resimKatmani(D.veri.kp), efsane: "penetrasyon" },
  { id: "numune", ad: "Numune noktaları", gerekir: "zemin", veri: "num", yap: numuneKatmani },
  { id: "balik", ad: "Balık izleri", gerekir: "taramalar", veri: "balik", yap: balikKatmani },
  { id: "sert", ad: "Sert nokta / nesne", gerekir: "taramalar", veri: "sert", yap: sertKatmani },
];
const SIRA = ["tum_golet", "batimetri", "zemin", "sertlik", "penetrasyon", "kontur", "kiyi", "rota", "yeni_rota", "numune", "balik", "sert"];

function katmanlariSifirla() {
  for (const l of Object.values(D.katmanlar)) D.harita?.removeLayer(l);
  D.katmanlar = {};
  D.acikKatman = new Set(["rota", "batimetri", "kontur"]);
  if (D.harita) { D.harita.remove(); D.harita = null; }
  D.haritaSigdi = false;
  if (D.isaret) D.isaret = null;
  $("#kesitCekmece").hidden = true;
}

function katmanlariKur() {
  const liste = $("#katmanListe");
  liste.innerHTML = "";
  for (const k of KATMANLAR) {
    const var_ = analizDurum(k.gerekir) === "bitti" && (!k.veri || D.veri[k.veri]);
    const sayi = k.id === "numune" && D.veri.num ? D.veri.num.features.length :
      k.id === "balik" && D.veri.balik ? D.veri.balik.features.length :
      k.id === "sert" && D.veri.sert ? D.veri.sert.features.length : null;
    const el = document.createElement("label");
    el.className = "katman" + (var_ ? "" : " kilitli");
    el.title = var_ ? "" : `${D.analizTanim?.[k.gerekir]?.ad || k.gerekir} çalıştırılınca açılır`;
    el.innerHTML = `<input type="checkbox" ${var_ && D.acikKatman.has(k.id) ? "checked" : ""} ${var_ ? "" : "disabled"}><span class="anahtar"></span>${esc(k.ad)}${sayi != null ? `<small>${sayi}</small>` : ""}${!var_ ? "<small>kilitli</small>" : ""}`;
    $("input", el).onchange = e => { e.target.checked ? D.acikKatman.add(k.id) : D.acikKatman.delete(k.id); katmanUygula(); };
    liste.append(el);
  }
  katmanUygula();
}

function katmanUygula() {
  if (!D.harita) return;
  for (const id of SIRA) {
    const k = KATMANLAR.find(x => x.id === id);
    const var_ = analizDurum(k.gerekir) === "bitti" && (!k.veri || D.veri[k.veri]);
    const ac = var_ && D.acikKatman.has(id);
    if (ac && !D.katmanlar[id]) { try { D.katmanlar[id] = k.yap(); } catch (e) { console.warn(id, e); continue; } }
    if (D.katmanlar[id]) { D.harita.removeLayer(D.katmanlar[id]); if (ac) D.katmanlar[id].addTo(D.harita); }
  }
  if (D.isaret) D.isaret.bringToFront?.();
  efsaneCiz();
}

function resimKatmani(k) { return L.imageOverlay(purl("web/" + k.png) + "?t=" + Date.now(), k.sinir, { opacity: 1, interactive: false }); }

function rotaKatmani() {
  const { lat, lon, dep } = D.veri.rota, { min, max } = D.veri.kb;
  const g = L.layerGroup();
  const ren = L.canvas({ padding: 0.3 });
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
    onEachFeature: (f, l) => l.bindTooltip(`${nf(f.properties.derinlik, 2)} m`, { sticky: true }),
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
    L.marker([a, lon[i]], { icon: L.divIcon({ className: "", html: `<div style="background:#facc15;color:#111;border-radius:50%;width:20px;height:20px;display:grid;place-items:center;font:600 11px system-ui;box-shadow:0 1px 4px #0008">${hat[i]}</div>`, iconSize: [20, 20] }) })
      .bindTooltip(i === 0 ? "Başlangıç — hat 1" : `Hat ${hat[i]}`).addTo(g);
  });
  return g;
}

function numuneKatmani() {
  return L.geoJSON(D.veri.num, {
    pointToLayer: (f, ll) => L.marker(ll, { icon: L.divIcon({ className: "", iconSize: [26, 26],
      html: `<div style="width:26px;height:26px;border-radius:50%;background:#ef4444;border:2px solid #fff;box-shadow:0 2px 8px #000a;display:grid;place-items:center;color:#fff;font:700 11px system-ui">★</div>` }) }),
    onEachFeature: (f, l) => l.bindPopup(`<b>${esc(f.properties.nokta)}</b><br>${esc(f.properties.beklenen_zemin)}<br>Derinlik ${nf(f.properties.derinlik_m, 2)} m<br><small>${f.geometry.coordinates[1].toFixed(6)}, ${f.geometry.coordinates[0].toFixed(6)}</small>`),
  });
}

function balikKatmani() {
  return L.geoJSON(D.veri.balik, {
    pointToLayer: (f, ll) => L.circleMarker(ll, { radius: 6, color: "#111", weight: 1, fillColor: f.properties.tur === "balik" ? "#fb923c" : "#22d3ee", fillOpacity: .95 }),
    onEachFeature: (f, l) => l.bindTooltip(`${f.properties.tur === "balik" ? "Balık izi" : "Gaz kabarcığı"} · ${nf(f.properties.derinlik, 2)} m · ${nf(f.properties.dk, 1)}. dk`),
  });
}

function sertKatmani() {
  return L.geoJSON(D.veri.sert, {
    pointToLayer: (f, ll) => L.circleMarker(ll, { radius: 9, color: "#f43f5e", weight: 3, fill: false }),
    onEachFeature: (f, l) => l.bindTooltip(`${esc(f.properties.no)}: ${esc(f.properties.tur)} · ${nf(f.properties.derinlik, 2)} m`),
  });
}

function efsaneCiz() {
  const e = $("#efsane");
  const acik = id => D.acikKatman.has(id) && D.katmanlar[id] && D.harita.hasLayer(D.katmanlar[id]);
  const grad = D.veri.renk ? `linear-gradient(90deg, ${D.veri.renk.join(",")})` : "";
  let h = "";
  if (acik("zemin") && D.veri.kz) h = `<b>Zemin sınıfları <span class="ince">(göreli)</span></b>` + D.veri.kz.siniflar.map(s => `<div class="sinif"><i style="background:${s.renk}"></i>${esc(s.ad)} <span class="ince">%${nf(s.alan_yuzde)}</span></div>`).join("");
  else if (acik("sertlik")) h = `<b>Dip sertliği</b><div class="skala" style="background:linear-gradient(90deg,#ffffe5,#fe9929,#662506)"></div><div class="skala-et"><span>yumuşak</span><span>sert</span></div>`;
  else if (acik("penetrasyon")) h = `<b>Penetrasyon</b><div class="skala" style="background:linear-gradient(90deg,#fff7fb,#74a9cf,#023858)"></div><div class="skala-et"><span>yüzeyden seker</span><span>tortuya girer</span></div>`;
  else if (acik("tum_golet") && D.veri.ktg) h = `<b>Tahmini derinlik (m)</b><div class="skala" style="background:${grad}"></div><div class="skala-et"><span>0</span><span>${nf(D.veri.ktg.max, 1)}</span></div>`;
  else if ((acik("batimetri") || acik("rota")) && D.veri.kb) h = `<b>Derinlik (m)</b><div class="skala" style="background:${grad}"></div><div class="skala-et"><span>${nf(D.veri.kb.min, 1)}</span><span>${nf(D.veri.kb.max, 1)}</span></div>`;
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
  $("#kesitCekmece").hidden = false;
  $("#kcBilgi").textContent = `${sureYaz(r.t[i] / 60)}. dk · derinlik ${nf(r.dep[i], 2)} m · ${r.lat[i].toFixed(6)}, ${r.lon[i].toFixed(6)}`;
  await kesitGetir(r.satir[i], 600, "bakir", $("#kcImg"), $("#kcCanvas"));
}

// ------------------------------------------------------------------ kesit
async function kesitGetir(satir, genislik, palet, img, cnv, yuk) {
  const no = ++D.kesitIstek;
  yuk?.classList.add("acik");
  try {
    const r = await fetch(purl(`kesit?merkez=${satir}&genislik=${genislik}&palet=${palet}`));
    if (!r.ok) throw new Error("Kesit alınamadı");
    const bilgi = JSON.parse(r.headers.get("X-Kesit")), dip = JSON.parse(r.headers.get("X-Dip"));
    const blob = await r.blob();
    if (no !== D.kesitIstek && img.id !== "kcImg") return;
    const u = URL.createObjectURL(blob);
    await new Promise(res => { img.onload = res; img.src = u; });
    URL.revokeObjectURL(img.dataset.u || ""); img.dataset.u = u;
    kesitUstCiz(cnv, bilgi, dip, satir);
    return bilgi;
  } catch (e) { bildir(e.message, true); }
  finally { yuk?.classList.remove("acik"); }
}
function kesitUstCiz(cnv, b, dip, satir) {
  const W = cnv.clientWidth, H = cnv.clientHeight, dpr = devicePixelRatio || 1;
  cnv.width = W * dpr; cnv.height = H * dpr;
  const c = cnv.getContext("2d"); c.scale(dpr, dpr); c.clearRect(0, 0, W, H);
  // derinlik olcegi
  c.font = "11px system-ui"; c.fillStyle = "rgba(255,255,255,.75)"; c.strokeStyle = "rgba(255,255,255,.12)";
  const adim = b.dmax > 12 ? 2 : b.dmax > 5 ? 1 : 0.5;
  for (let z = adim; z < b.dmax; z += adim) {
    const y = z / b.dmax * H;
    c.beginPath(); c.moveTo(0, y); c.lineTo(W, y); c.stroke();
    c.fillText(`${nf(z, adim < 1 ? 1 : 0)} m`, 6, y - 3);
  }
  // merkez cizgisi
  const x = (satir - b.a0) / (b.a1 - b.a0) * W;
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
  $("#okZaman").textContent = `${sureYaz(b.t)} dk`;
  $("#okDerinlik").textContent = b.dep == null ? "–" : `${nf(b.dep, 2)} m`;
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
  z.t.forEach((t, i) => { if (z.dep[i] != null) c.lineTo(t / tmax * W, z.dep[i] / dmax * H); });
  c.lineTo(W, H); c.closePath();
  const g2 = c.createLinearGradient(0, 0, 0, H); g2.addColorStop(0, "#b45309"); g2.addColorStop(1, "#3b1d06");
  c.fillStyle = g2; c.fill();
  c.strokeStyle = "#fbbf24"; c.lineWidth = 1; c.beginPath();
  let ilk = true; z.t.forEach((t, i) => { if (z.dep[i] == null) { ilk = true; return; } const x = t / tmax * W, y = z.dep[i] / dmax * H; ilk ? c.moveTo(x, y) : c.lineTo(x, y); ilk = false; });
  c.stroke();
  const b = satirBilgi(D.sonarSatir), x = b.t / tmax * W;
  const gen = +$("#genislik").value / D.veri.ozet.ping_hz / 60 / tmax * W;
  c.fillStyle = "rgba(34,211,238,.18)"; c.fillRect(x - gen / 2, 0, gen, H);
  c.strokeStyle = "#22d3ee"; c.lineWidth = 2; c.beginPath(); c.moveTo(x, 0); c.lineTo(x, H); c.stroke();
  c.fillStyle = "rgba(255,255,255,.6)"; c.font = "11px system-ui";
  for (let m = 0; m <= tmax; m += tmax > 30 ? 10 : 5) c.fillText(`${m} dk`, m / tmax * W + 3, H - 5);
}
function sonarKur() {
  const gb = $(".genel-bakis");
  if (!$("#genelCanvas")) {
    gb.innerHTML = `<canvas id="genelCanvas" style="display:block;width:100%;height:120px"></canvas>`;
    gb.style.background = "none";
    $("#genelCanvas").onclick = e => {
      const r = e.target.getBoundingClientRect(), z = D.veri.zaman;
      const t = (e.clientX - r.left) / r.width * z.t[z.t.length - 1];
      let i = z.t.findIndex(v => v >= t); if (i < 0) i = z.t.length - 1;
      sonarGit(z.satir[i]);
    };
  }
  $(".genel-bakis").previousElementSibling.innerHTML = `Tüm kayıt — derinlik profili <span class="ince">tıkla: o ana git</span>`;
  sonarGit(D.sonarSatir, true);
}
function sonarBagla() {
  $("#zamanCubuk").oninput = e => sonarGit(+e.target.value);
  $("#genislik").onchange = () => sonarGit(D.sonarSatir, true);
  $("#palet").onchange = () => sonarGit(D.sonarSatir, true);
  $("#oynat").onclick = oynat;
  $("#sonarImg").parentElement.onclick = e => {
    const r = e.currentTarget.getBoundingClientRect(), g = +$("#genislik").value;
    sonarGit(D.sonarSatir + ((e.clientX - r.left) / r.width - 0.5) * g);
  };
  addEventListener("keydown", e => {
    if (D.sekme !== "sonar" || e.target.matches("input[type=text],input:not([type]),select")) return;
    const g = +$("#genislik").value;
    if (e.key === "ArrowRight") { e.preventDefault(); sonarGit(D.sonarSatir + g / 4); }
    if (e.key === "ArrowLeft") { e.preventDefault(); sonarGit(D.sonarSatir - g / 4); }
    if (e.key === " ") { e.preventDefault(); oynat(); }
  });
  addEventListener("resize", () => { if (D.sekme === "sonar") genelCiz(); });
}

// ------------------------------------------------------------------ grafikler
function grafikKur() {
  if (D.grafikHazir) return;
  D.grafikler.forEach(g => g.destroy()); D.grafikler = [];
  const z = D.veri.zaman;
  Chart.defaults.color = "#8b9ab3"; Chart.defaults.borderColor = "rgba(148,170,210,.12)";
  Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
  const ortak = (birim, ters = false) => ({
    responsive: true, maintainAspectRatio: false, animation: false, parsing: false, normalized: true,
    interaction: { mode: "nearest", axis: "x", intersect: false },
    plugins: { legend: { display: false }, tooltip: { callbacks: { title: it => `${sureYaz(it[0].parsed.x)}. dk`, label: it => `${nf(it.parsed.y, 2)} ${birim}` } },
      decimation: { enabled: true, algorithm: "min-max" } },
    scales: { x: { type: "linear", title: { display: true, text: "Kayıt süresi (dk)" } }, y: { reverse: ters, title: { display: true, text: birim } } },
    onClick: (e, el, ch) => { const x = ch.scales.x.getValueForPixel(e.x); let i = z.t.findIndex(v => v >= x); if (i < 0) i = z.t.length - 1; D.sonarSatir = z.satir[i]; sekmeAc("sonar"); },
  });
  const seri = (k) => z.t.map((t, i) => ({ x: t, y: z[k][i] })).filter(p => p.y != null);
  const yap = (id, k, renk, birim, ters) => new Chart($(id), {
    type: "line", data: { datasets: [{ data: seri(k), borderColor: renk, borderWidth: 1.4, pointRadius: 0, fill: ters ? "start" : "origin",
      backgroundColor: renk + "22", tension: 0 }] }, options: ortak(birim, ters) });
  D.grafikler = [yap("#gDerinlik", "dep", "#22d3ee", "m", true), yap("#gHiz", "hiz", "#fbbf24", "km/sa"), yap("#gSicaklik", "sic", "#f87171", "°C")];
  D.grafikHazir = true;
}

// ------------------------------------------------------------------ analiz kartlari
const ANALIZ_BILGI = {
  temel: { ikon: "◎", aciklama: "RSD dosyasını çözer; rota, derinlik haritası, eş derinlik çizgileri, sonar görüntüleri ve zaman grafikleri.", sure: "~1 dk" },
  zemin: { ikon: "▦", aciklama: "Dip yankısının şeklinden sertlik, penetrasyon ve sönümlenme ölçer; zemini 3 göreli sınıfa ayırır ve dip numunesi noktaları önerir (GPX).", sure: "~8 dk" },
  uydu: { ikon: "◰", aciklama: "Uydu görüntüsünden kıyı çizgisini çıkarır; toplam hacim, dip eğimi, kapsama ve eksik alanlar için yeni tarama rotası (GPX). İnternet gerekir.", sure: "~1 dk" },
  taramalar: { ikon: "≋", aciklama: "Su kolonunda balık ve gaz kabarcığı izleri, dipte kaya / batık nesne ve su bitkisi örtüsü taraması.", sure: "~6 dk" },
  rapor: { ikon: "⎙", aciklama: "Çalışmış tüm analizlerin bulgularını ve görsellerini tek dosyalık HTML rapora toplar (tarayıcıdan PDF alınabilir).", sure: "~10 sn" },
};
function analizSonuc(t) {
  const v = D.veri, o = [];
  if (t === "temel" && v.ozet) o.push(["Derinlik", `${nf(v.ozet.derinlik_min, 1)}–${nf(v.ozet.derinlik_max, 1)} m`], ["Haritalanan", `${nf(v.ozet.haritalanan_alan_m2)} m²`]);
  if (t === "zemin" && v.kz) v.kz.siniflar.slice(0, 2).forEach(s => o.push([s.ad.split(" (")[0], `%${nf(s.alan_yuzde)}`]));
  if (t === "uydu" && v.hacim) o.push(["Toplam hacim", `${nf(v.hacim.tum_golet_hacmi_m3_kiyi0m)}–${nf(v.hacim["tum_golet_hacmi_m3_kiyi0.5m"])} m³`], ["Ölçülen", `%${nf(v.hacim.olculen_alan_yuzde)}`],
    ["Yeni rota", `${v.hacim.yeni_rota_hat_sayisi} hat · ${nf(v.hacim.yeni_rota_sure_dk)} dk`], ["Dip eğimi", `${nf(v.hacim.egim_medyan_derece, 1)}°`]);
  if (t === "taramalar" && v.tar) o.push(["Balık izi", nf(v.tar.balik)], ["Gaz kabarcığı", v.tar.kabarcik ? nf(v.tar.kabarcik) : "yok"],
    ["Sert nokta", v.tar.sert_nokta ? nf(v.tar.sert_nokta) : "yok"], ["Bitki kaplama", `%${nf(v.tar.bitki_kaplama_ort_yuzde, 1)}`]);
  return o;
}
function analizKartlariCiz() {
  const tan = D.analizTanim; if (!tan || !D.proje) return;
  $("#analizKartlar").innerHTML = Object.entries(tan).map(([t, a]) => {
    const s = D.proje.analizler[t] || {}, d = s.durum || "yok";
    const eksik = a.gerekir.filter(g => analizDurum(g) !== "bitti");
    const bilgi = ANALIZ_BILGI[t] || {};
    const sonuc = d === "bitti" ? analizSonuc(t) : [];
    let alt;
    if (d === "calisiyor" || d === "bekliyor") alt = `<div style="flex:1"><div class="cubuk"><i style="width:${Math.max(3, (s.ilerleme || 0) * 100)}%"></i></div>
      <small>${d === "bekliyor" ? "Sırada" : esc(s.adim || "")} · %${nf((s.ilerleme || 0) * 100)}</small></div>`;
    else if (t === "rapor" && d === "bitti") alt = `<a class="btn" href="${purl("dosya/rapor.html")}" target="_blank" rel="noopener">Raporu aç</a>
      <button class="btn hayalet kucuk" data-calistir="${t}">Yeniden oluştur</button>`;
    else alt = `<button class="btn ${d === "bitti" ? "hayalet kucuk" : ""}" data-calistir="${t}" ${eksik.length ? "disabled" : ""}>${d === "bitti" ? "Yeniden çalıştır" : d === "hata" ? "Tekrar dene" : "Çalıştır"}</button>
      <small>${eksik.length ? `Önce: ${eksik.map(g => tan[g].ad).join(", ")}` : `süre ${bilgi.sure || ""}`}</small>`;
    return `<div class="analiz-kart ${d}">
      <div class="ak-ust"><div class="ak-ikon">${bilgi.ikon || "•"}</div><b>${esc(a.ad)}</b><span class="durum ${d}">${durumAd[d] || "Çalışmadı"}</span></div>
      <p>${esc(bilgi.aciklama || "")}</p>
      ${sonuc.length ? `<div class="ak-sonuc">${sonuc.map(([k, v]) => `<div><span>${esc(k)}</span><b>${esc(v)}</b></div>`).join("")}</div>` : ""}
      ${d === "hata" ? `<div class="ak-mesaj">${esc(s.mesaj || "")}</div>` : ""}
      <div class="ak-alt">${alt}</div></div>`;
  }).join("");
  $$("[data-calistir]").forEach(b => b.onclick = () => analizBaslat(b.dataset.calistir));
}
async function analizBaslat(t) {
  try { D.proje = await api(purl(`analiz/${t}`), { method: "POST" }); D.eskiDurum[t] = "bekliyor"; durumGuncelle(); }
  catch (e) { bildir(e.message, true); }
}

// ------------------------------------------------------------------ dosyalar
const KLASOR_AD = { "": "Rapor", grafikler: "Sonar görüntüleri ve grafikler", uydu: "Uydu üzerinde haritalar", zemin: "Zemin sınıflaması ve numune",
  morfoloji: "Hacim, eğim ve rota", sertnokta: "Sert nokta taraması", bitki: "Bitki örtüsü", balik: "Balık ve kabarcık" };
async function dosyalarCiz() {
  const l = await api(purl("dosyalar"));
  const gruplar = {};
  l.forEach(f => (gruplar[f.klasor] ??= []).push(f));
  const sira = ["", "grafikler", "uydu", "zemin", "morfoloji", "sertnokta", "bitki", "balik"];
  $("#dosyaListe").innerHTML = sira.filter(k => gruplar[k]).map(k => {
    const res = gruplar[k].filter(f => f.tur === "png"), diger = gruplar[k].filter(f => f.tur !== "png");
    return `<div class="dosya-grup"><h3>${KLASOR_AD[k] || k}</h3>
      ${res.length ? `<div class="galeri">${res.map(f => `<div class="galeri-oge" data-yol="${esc(f.yol)}"><img loading="lazy" src="${purl("dosya/" + f.yol)}" alt=""><span>${esc(f.yol.split("/").pop())}</span></div>`).join("")}</div>` : ""}
      ${diger.length ? `<div class="indirmeler" style="margin-top:10px">${diger.map(f => `<a class="indirme" href="${purl("dosya/" + f.yol)}${f.tur === "html" ? "" : "?indir=1"}" ${f.tur === "html" ? 'target="_blank" rel="noopener"' : ""}><em>${f.tur}</em>${esc(f.yol.split("/").pop())}<span class="ince">${nf(f.boyut / 1024)} KB</span></a>`).join("")}</div>` : ""}
    </div>`;
  }).join("") || `<p class="aciklama">Henüz dosya yok.</p>`;
  $$(".galeri-oge").forEach(g => g.onclick = () => {
    const b = $("#buyutec"), u = purl("dosya/" + g.dataset.yol);
    $("img", b).src = u; $(".buyutec-alt span", b).textContent = g.dataset.yol; $(".buyutec-alt a", b).href = u + "?indir=1"; b.hidden = false;
  });
}

// ------------------------------------------------------------------ sekmeler / ust islemler
function sekmeAc(s) {
  D.sekme = s;
  $$("#sekmeler button").forEach(b => b.classList.toggle("aktif", b.dataset.sekme === s));
  $$(".sekme").forEach(x => x.hidden = x.id !== "sekme-" + s);
  if (s === "harita" && D.harita) setTimeout(() => {
    D.harita.invalidateSize();
    if (!D.haritaSigdi) {
      D.harita.fitBounds(D.veri.kb?.sinir || D.veri.ozet.sinir, { paddingTopLeft: [40, 50], paddingBottomRight: [270, 40] });
      D.haritaSigdi = true;
    }
  }, 30);
  if (s === "sonar") sonarKur();
  if (s === "grafik") grafikKur();
  if (s === "analiz") analizKartlariCiz();
  if (s === "dosya") dosyalarCiz();
}
function ustBagla() {
  $$("#sekmeler button").forEach(b => b.onclick = () => sekmeAc(b.dataset.sekme));
  $("#projeAd").onchange = async e => {
    try { await api(`/api/projeler/${D.pid}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ad: e.target.value }) }); listeYukle(); }
    catch (er) { bildir(er.message, true); }
  };
  $("#projeAd").onkeydown = e => { if (e.key === "Enter") e.target.blur(); };
  $("#silBtn").onclick = async () => {
    if (!confirm(`"${D.proje.ad}" projesi ve tüm çıktıları kalıcı olarak silinsin mi?`)) return;
    try { await api(`/api/projeler/${D.pid}`, { method: "DELETE" }); D.pid = null; katmanlariSifirla(); $("#proje").hidden = true; $("#karsilama").hidden = false; history.replaceState(null, "", "#"); listeYukle(); bildir("Proje silindi"); }
    catch (e) { bildir(e.message, true); }
  };
  $("#raporBtn").onclick = () => {
    const d = analizDurum("rapor");
    if (d === "bitti") window.open(purl("dosya/rapor.html"), "_blank", "noopener");
    else if (d === "calisiyor" || d === "bekliyor") bildir("Rapor hazırlanıyor…");
    else { analizBaslat("rapor"); bildir("Rapor hazırlanıyor; bitince bu düğmeyle açılır"); }
  };
  $("#kcKapat").onclick = () => { $("#kesitCekmece").hidden = true; if (D.isaret) D.harita.removeLayer(D.isaret); };
  $("#kcSonar").onclick = () => sekmeAc("sonar");
  const bu = $("#buyutec");
  bu.onclick = e => { if (e.target === bu || e.target.classList.contains("kapat")) bu.hidden = true; };
  addEventListener("keydown", e => { if (e.key === "Escape") bu.hidden = true; });
}

// ------------------------------------------------------------------ baslangic
(async function () {
  yuklemeBagla(); ustBagla(); sonarBagla();
  try { D.analizTanim = await api("/api/analizler"); } catch (e) { bildir("Sunucuya bağlanılamadı", true); }
  await listeYukle();
  const h = location.hash.slice(1);
  if (h && D.projeler.some(p => p.id === h)) projeAc(h);
})();
