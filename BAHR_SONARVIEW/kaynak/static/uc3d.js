/* BAHR SONARVIEW - 3B topografya sekmesi (Three.js).
   Yalnizca secilen alan (dikdortgen ya da cokgen) icin derinlik yuzeyi uretilir. app.js'in $, D, t, nf, uz, api ... ogelerini kullanir. */
"use strict";

const UC = {
  r: null, sahne: null, kam: null, hazir: false, canli: false, kirli: true, istek: 0,
  veri: null, E: 5, mod: "derinlik", kontur: true, su: true, tahmin: true, adim: 0, kip: "dikdortgen",
  obj: {}, hedef: null, yar: 100, az: 0.55, kut: 1.0, merkez: { x: 0, z: 0 }, taban: 0, isik: null,
  hover: null, surukle: null,
};
const UC_RAMPA = {
  egim: ["#0b1220", "#3b0f70", "#8c2981", "#de4968", "#fe9f6d", "#fcfdbf"],
  derinlik: ["#fde725", "#5ec962", "#21918c", "#3b528b", "#440154"],
};
const UC_KAYNAK = { 1: "#34d399", 2: "#fbbf24" };

function ucHex(h) { return [parseInt(h.slice(1, 3), 16) / 255, parseInt(h.slice(3, 5), 16) / 255, parseInt(h.slice(5, 7), 16) / 255]; }
function ucRampa(liste, f) {
  f = Math.max(0, Math.min(1, f)) * (liste.length - 1);
  const i = Math.min(liste.length - 2, Math.floor(f)), a = ucHex(liste[i]), b = ucHex(liste[i + 1]), k = f - i;
  return [a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k, a[2] + (b[2] - a[2]) * k];
}

// ------------------------------------------------------------------ baslatma
function ucBaslat() {
  if (UC.hazir) return true;
  const cnv = $("#ucCanvas");
  try {
    UC.r = new THREE.WebGLRenderer({ canvas: cnv, antialias: true, alpha: true });
  } catch (e) {
    ucDurum(t("Bu bilgisayarda 3B görüntüleme (WebGL) kullanılamıyor."), true); return false;
  }
  UC.r.setPixelRatio(Math.min(devicePixelRatio || 1, 2));
  UC.r.setClearColor(0x000000, 0);
  UC.sahne = new THREE.Scene();
  UC.kam = new THREE.PerspectiveCamera(38, 1, 0.1, 20000);
  UC.sahne.add(new THREE.AmbientLight(0xffffff, 0.62));
  UC.isik = new THREE.DirectionalLight(0xffffff, 0.85);
  UC.isik.position.set(-60, 120, 80);
  UC.sahne.add(UC.isik);
  const ikinci = new THREE.DirectionalLight(0x9bd8ff, 0.25);
  ikinci.position.set(80, 40, -60);
  UC.sahne.add(ikinci);
  new ResizeObserver(ucBoyut).observe($("#ucSahne"));
  ucEtkilesim(cnv);
  UC.hazir = true;
  ucBoyut();
  return true;
}
function ucBoyut() {
  if (!UC.r) return;
  const el = $("#ucSahne"), w = el.clientWidth, h = el.clientHeight;
  if (w < 10 || h < 10) return;
  UC.r.setSize(w, h, false);
  UC.kam.aspect = w / h; UC.kam.updateProjectionMatrix();
  UC.kirli = true;
}
function ucDongu() {
  if (!UC.canli) return;
  if (UC.kirli && UC.r) { UC.r.render(UC.sahne, UC.kam); UC.kirli = false; }
  requestAnimationFrame(ucDongu);
}
function ucKameraGuncelle() {
  const { yar, az, kut, hedef } = UC;
  UC.kam.position.set(hedef.x + yar * Math.sin(kut) * Math.sin(az), hedef.y + yar * Math.cos(kut), hedef.z + yar * Math.sin(kut) * Math.cos(az));
  UC.kam.lookAt(hedef);
  $("#ucPusula").style.transform = `rotate(${(az * 180 / Math.PI).toFixed(1)}deg)`;
  UC.kirli = true;
}
function ucGorunum(ad) {
  const g = UC.gen || 100;
  if (ad === "ust") { UC.kut = 0.001; UC.az = 0; UC.yar = g * 1.9; }
  else if (ad === "yan") { UC.kut = 1.42; UC.az = 0; UC.yar = g * 2.1; }
  else { UC.kut = 1.0; UC.az = 0.55; UC.yar = g * 2.1; }
  UC.hedef = new THREE.Vector3(UC.merkez.x, UC.taban, UC.merkez.z);
  ucKameraGuncelle();
}

// ------------------------------------------------------------------ fare / dokunma
function ucEtkilesim(cnv) {
  cnv.addEventListener("contextmenu", e => e.preventDefault());
  cnv.addEventListener("pointerdown", e => {
    cnv.setPointerCapture(e.pointerId);
    UC.surukle = { x: e.clientX, y: e.clientY, kaydir: e.button === 2 || e.shiftKey || e.button === 1 };
    $("#ucOkuma").hidden = true;
  });
  cnv.addEventListener("pointerup", e => { UC.surukle = null; try { cnv.releasePointerCapture(e.pointerId); } catch { /* yok */ } });
  cnv.addEventListener("pointermove", e => {
    const s = UC.surukle;
    if (!s) { ucUzerinde(e); return; }
    const dx = e.clientX - s.x, dy = e.clientY - s.y;
    s.x = e.clientX; s.y = e.clientY;
    if (s.kaydir) {
      const k = UC.yar * 0.0011;
      const sag = new THREE.Vector3().setFromMatrixColumn(UC.kam.matrix, 0), yuk = new THREE.Vector3().setFromMatrixColumn(UC.kam.matrix, 1);
      UC.hedef.addScaledVector(sag, -dx * k).addScaledVector(yuk, dy * k);
    } else {
      UC.az -= dx * 0.0075;
      UC.kut = Math.max(0.001, Math.min(1.5, UC.kut - dy * 0.0075));
    }
    ucKameraGuncelle();
  });
  cnv.addEventListener("wheel", e => {
    e.preventDefault();
    UC.yar = Math.max(UC.gen * 0.08, Math.min(UC.gen * 6, UC.yar * Math.pow(1.0015, e.deltaY)));
    ucKameraGuncelle();
  }, { passive: false });
  cnv.addEventListener("dblclick", () => ucGorunum("egik"));
  cnv.addEventListener("pointerleave", () => { $("#ucOkuma").hidden = true; ucIsaretKaldir(); });
}
function ucUzerinde(e) {
  const m = UC.obj.yuzey;
  if (!m) return;
  const simdi = performance.now();
  if (simdi - (ucUzerinde.son || 0) < 30) return;               // en cok ~33 okuma / sn
  ucUzerinde.son = simdi;
  {
    const r = $("#ucCanvas").getBoundingClientRect();
    const nd = new THREE.Vector2(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
    const rc = new THREE.Raycaster();
    rc.setFromCamera(nd, UC.kam);
    const hit = rc.intersectObject(m, false)[0];
    const o = $("#ucOkuma");
    if (!hit) { o.hidden = true; ucIsaretKaldir(); return; }
    const v = UC.veri, p = hit.point;
    const der = -p.y / UC.E, dogu = p.x + UC.cx, kuzey = UC.cy - p.z;
    const fi = hit.face ? hit.face.a : 0, kaynak = UC.vk?.[fi] ?? 1;
    o.innerHTML = `<b>${uz(der, 2)}</b><span>${kaynak === 2 ? t("tahmin") : t("ölçüm")}</span><small>${nf(uzc(dogu), 1)} ${birim()} ${t("doğu")} · ${nf(uzc(kuzey), 1)} ${birim()} ${t("kuzey")}</small>`;
    const kr = $("#ucSahne").getBoundingClientRect();
    o.style.left = Math.min(kr.width - 190, e.clientX - kr.left + 14) + "px";
    o.style.top = Math.max(8, e.clientY - kr.top - 56) + "px";
    o.hidden = false;
    ucIsaret(p);
  }
}
function ucIsaret(p) {
  if (!UC.obj.isaret) {
    const g = new THREE.Group();
    g.add(new THREE.Mesh(new THREE.SphereGeometry(1, 14, 10), new THREE.MeshBasicMaterial({ color: 0xffffff })));
    const c = new THREE.Line(new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(0, 0, 0), new THREE.Vector3(0, 1, 0)]), new THREE.LineBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.7 }));
    c.name = "cizgi"; g.add(c);
    UC.sahne.add(g); UC.obj.isaret = g;
  }
  const g = UC.obj.isaret, s = UC.gen * 0.006;
  g.visible = true; g.position.copy(p);
  g.children[0].scale.setScalar(s);
  g.children[1].scale.set(1, -p.y, 1);                 // yuzeyden su seviyesine
  g.children[1].position.set(0, 0, 0);
  UC.kirli = true;
}
function ucIsaretKaldir() { if (UC.obj.isaret?.visible) { UC.obj.isaret.visible = false; UC.kirli = true; } }

// ------------------------------------------------------------------ sekme
function uc3dAc() {
  if (!UC.hazir && !ucBaslat()) return;
  UC.canli = true;
  ucBoyut();
  requestAnimationFrame(ucDongu);
  const tur = D.analizTanim, uyduVar = analizDurum("uydu") === "bitti";
  $("#ucTahmin").disabled = !uyduVar;
  if (!uyduVar) { UC.tahmin = false; $("#ucTahmin").checked = false; }
  ucAlanYazi();
  if (!UC.veri && !UC.yukleniyor) uc3dYukle(true);
  else UC.kirli = true;
}
function uc3dDur() { UC.canli = false; }
function uc3dSifirla() {
  UC.veri = null; UC.istek++; UC.yukleniyor = false;
  ucTemizle();
  if (UC.sahne) UC.kirli = true;
}
function ucDurum(m, hata = false) {
  const e = $("#ucDurum");
  e.hidden = !m; e.textContent = m || ""; e.className = "uc-durum" + (hata ? " hata" : "");
}
function ucAlanYazi() {
  const a = D.alan3d;
  $("#ucAlanBilgi").textContent = a ? `${a.tip === "dikdortgen" ? t("Dikdörtgen") : t("Çokgen")} · ${a.noktalar.length} ${t("köşe")}` : t("Tüm ölçülen alan");
  $("#ucAlanTemizle").hidden = !a;
}
async function uc3dYukle(yeniAlan = false) {
  if (!D.pid) return;
  const no = ++UC.istek;
  UC.yukleniyor = true;
  ucDurum(t("3B yüzey hazırlanıyor…"));
  try {
    const v = await api(purl("yuzey3d"), { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ poligon: D.alan3d?.noktalar || null, tahmin: UC.tahmin, adim: UC.adim }) });
    if (no !== UC.istek) return;
    UC.veri = v;
    const gen = Math.max(v.ozet.genislik_m, v.ozet.yukseklik_m), rel = Math.max(0.3, v.ozet.max - v.ozet.min);
    if (yeniAlan) {
      UC.E = Math.max(1, Math.min(20, Math.round(0.16 * gen / rel)));
      $("#ucE").value = UC.E; $("#ucEYazi").textContent = `×${UC.E}`;
    }
    ucMeshKur();
    if (yeniAlan) ucGorunum("egik");
    ucBilgiYaz();
    ucDurum("");
  } catch (e) {
    if (no !== UC.istek) return;
    UC.veri = null; ucTemizle(); ucBilgiYaz();
    ucDurum(e.message, true);
  } finally { if (no === UC.istek) UC.yukleniyor = false; }
}

// ------------------------------------------------------------------ ag olusturma
function ucTemizle() {
  for (const k of Object.keys(UC.obj)) {
    const o = UC.obj[k];
    if (k === "isaret") { o.visible = false; continue; }
    UC.sahne?.remove(o);
    o.traverse?.(n => { n.geometry?.dispose(); n.material?.dispose?.(); });
    delete UC.obj[k];
  }
  UC.kirli = true;
}
function ucRenkSec(mod, i, d, min, max, v, egim) {
  if (mod === "egim") return ucRampa(UC_RAMPA.egim, egim[i] / 25);
  if (mod === "zemin") {
    const sc = v.s?.[i], sn = D.veri.kz?.siniflar;
    return sc == null || !sn?.[sc] ? [0.45, 0.47, 0.5] : ucHex(sn[sc].renk);
  }
  if (mod === "kaynak") return ucHex(UC_KAYNAK[v.k[i]] || "#64748b");
  return ucRampa(D.veri.renk || UC_RAMPA.derinlik, (d - min) / ((max - min) || 1));
}
function ucMeshKur() {
  ucTemizle();
  const v = UC.veri, nx = v.nx, ny = v.ny, h = v.h, E = UC.E, Z = v.z;
  const idx = new Int32Array(nx * ny).fill(-1);
  UC.cx = nx * h / 2; UC.cy = ny * h / 2;
  const px = [], pz = [], dep = [], hu = [];                  // vertex dizileri
  for (let r = 0; r < ny; r++) for (let c = 0; c < nx; c++) {
    const i = r * nx + c;
    if (Z[i] == null) continue;
    idx[i] = px.length; hu.push(i);
    px.push((c + 0.5) * h - UC.cx); pz.push((r + 0.5) * h - UC.cy); dep.push(Z[i]);
  }
  const n = px.length;
  const min = v.ozet.min, max = v.ozet.max;
  // egim (derece): merkezi farklar
  const egim = new Float32Array(nx * ny);
  const dz = (r, c) => (r >= 0 && r < ny && c >= 0 && c < nx ? Z[r * nx + c] : null);
  for (const i of hu) {
    const r = Math.floor(i / nx), c = i % nx, d0 = Z[i];
    const gx = ((dz(r, c + 1) ?? d0) - (dz(r, c - 1) ?? d0)) / ((dz(r, c + 1) != null && dz(r, c - 1) != null ? 2 : 1) * h);
    const gy = ((dz(r + 1, c) ?? d0) - (dz(r - 1, c) ?? d0)) / ((dz(r + 1, c) != null && dz(r - 1, c) != null ? 2 : 1) * h);
    egim[i] = Math.atan(Math.hypot(gx, gy)) * 180 / Math.PI;
  }
  // ucgenler
  const tri = [];
  const ekle = (a, b, c) => {
    const ux = px[b] - px[a], uz_ = pz[b] - pz[a], wx = px[c] - px[a], wz = pz[c] - pz[a];
    if (uz_ * wx - ux * wz > 0) tri.push(a, b, c); else tri.push(a, c, b);     // normal yukari bakacak sekilde
  };
  for (let r = 0; r < ny - 1; r++) for (let c = 0; c < nx - 1; c++) {
    const a = idx[r * nx + c], b = idx[r * nx + c + 1], d = idx[(r + 1) * nx + c], e = idx[(r + 1) * nx + c + 1];
    const var_ = (a >= 0) + (b >= 0) + (d >= 0) + (e >= 0);
    if (var_ === 4) {
      if (Math.abs(dep[a] - dep[e]) <= Math.abs(dep[b] - dep[d])) { ekle(a, d, e); ekle(a, e, b); } else { ekle(a, d, b); ekle(b, d, e); }
    } else if (var_ === 3) {
      const l = [a, b, d, e].filter(q => q >= 0); ekle(l[0], l[1], l[2]);
    }
  }
  if (!tri.length) { ucDurum(t("Seçilen alan 3B yüzey için çok dar ya da parçalı."), true); return; }
  UC.tri = tri; UC.px = px; UC.pz = pz; UC.dep = dep;
  // koordinat ve renkler
  const pos = new Float32Array(n * 3), col = new Float32Array(n * 3);
  UC.vk = v.k ? hu.map(i => v.k[i]) : null;
  for (let q = 0; q < n; q++) {
    pos[q * 3] = px[q]; pos[q * 3 + 1] = -dep[q] * E; pos[q * 3 + 2] = pz[q];
    const rgb = ucRenkSec(UC.mod, hu[q], dep[q], min, max, v, egim);
    col[q * 3] = rgb[0]; col[q * 3 + 1] = rgb[1]; col[q * 3 + 2] = rgb[2];
  }
  UC.hu = hu; UC.egim = egim;
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  g.setAttribute("color", new THREE.BufferAttribute(col, 3));
  g.setIndex(tri);
  g.computeVertexNormals();
  const yuzey = new THREE.Mesh(g, new THREE.MeshLambertMaterial({ vertexColors: true, side: THREE.DoubleSide, polygonOffset: true, polygonOffsetFactor: 1, polygonOffsetUnits: 1 }));
  UC.sahne.add(yuzey); UC.obj.yuzey = yuzey;
  // olcu / merkez
  let x0 = 1e9, x1 = -1e9, z0 = 1e9, z1 = -1e9;
  for (let q = 0; q < n; q++) { x0 = Math.min(x0, px[q]); x1 = Math.max(x1, px[q]); z0 = Math.min(z0, pz[q]); z1 = Math.max(z1, pz[q]); }
  UC.merkez = { x: (x0 + x1) / 2, z: (z0 + z1) / 2 };
  UC.gen = Math.max(x1 - x0, z1 - z0, 10);
  UC.taban = -((min + max) / 2) * E * 0.7;
  UC.zemin_y = -max * E - Math.max(1.2, 0.07 * UC.gen);
  // yan duvar: sinir kenarlari (yonlu kenarin tersi yoksa sinirdir)
  const kenar = new Map();
  for (let i = 0; i < tri.length; i += 3) for (let k = 0; k < 3; k++) { const a = tri[i + k], b = tri[i + (k + 1) % 3]; kenar.set(a * n + b, [a, b]); }
  const sinir = [];
  for (const [, [a, b]] of kenar) if (!kenar.has(b * n + a)) sinir.push([a, b]);
  UC.sinir = sinir;
  if (sinir.length) {
    const sp = [], sc = [], si = [];
    const dark = (q, f) => [col[q * 3] * f, col[q * 3 + 1] * f, col[q * 3 + 2] * f];
    const fy = UC.zemin_y;
    sinir.forEach(([a, b], j) => {
      const ya = -dep[a] * E, yb = -dep[b] * E, o = j * 4;
      sp.push(px[a], ya, pz[a], px[a], fy, pz[a], px[b], yb, pz[b], px[b], fy, pz[b]);
      const ca = dark(a, 0.55), cb = dark(b, 0.55), kf = [0.06, 0.11, 0.18];
      sc.push(...ca, ...kf, ...cb, ...kf);
      si.push(o, o + 1, o + 2, o + 2, o + 1, o + 3);
    });
    const wg = new THREE.BufferGeometry();
    wg.setAttribute("position", new THREE.BufferAttribute(new Float32Array(sp), 3));
    wg.setAttribute("color", new THREE.BufferAttribute(new Float32Array(sc), 3));
    wg.setIndex(si);
    const duvar = new THREE.Mesh(wg, new THREE.MeshBasicMaterial({ vertexColors: true, side: THREE.DoubleSide }));
    UC.sahne.add(duvar); UC.obj.duvar = duvar;
  }
  // su yuzeyi: ayni ucgenler, y = 0
  const wp = new Float32Array(n * 3);
  for (let q = 0; q < n; q++) { wp[q * 3] = px[q]; wp[q * 3 + 1] = 0; wp[q * 3 + 2] = pz[q]; }
  const sg = new THREE.BufferGeometry();
  sg.setAttribute("position", new THREE.BufferAttribute(wp, 3)); sg.setIndex(tri);
  const su = new THREE.Mesh(sg, new THREE.MeshBasicMaterial({ color: 0x38bdf8, transparent: true, opacity: 0.2, depthWrite: false, side: THREE.DoubleSide }));
  su.renderOrder = 2; su.visible = UC.su;
  UC.sahne.add(su); UC.obj.su = su;
  ucKonturKur();
  ucEfsane();
  UC.kirli = true;
}
function ucKonturAraligi(min, max) {
  const a = D.ayar?.kontur_araligi;
  if (a > 0 && (max - min) / a < 60) return a;
  for (const s of [0.1, 0.25, 0.5, 1, 2, 5, 10, 25]) if ((max - min) / s <= 14) return s;
  return 50;
}
function ucKonturKur() {
  if (UC.obj.kontur) { UC.sahne.remove(UC.obj.kontur); UC.obj.kontur.geometry.dispose(); delete UC.obj.kontur; }
  if (!UC.veri || !UC.tri) return;
  const { px, pz, dep, tri, E } = UC, { min, max } = UC.veri.ozet;
  const adim = ucKonturAraligi(min, max), seg = [];
  for (let L = Math.ceil(min / adim) * adim; L < max; L += adim) {
    for (let i = 0; i < tri.length; i += 3) {
      const a = tri[i], b = tri[i + 1], c = tri[i + 2], da = dep[a] - L, db = dep[b] - L, dc = dep[c] - L;
      if ((da > 0) === (db > 0) && (db > 0) === (dc > 0)) continue;
      const nokta = [];
      for (const [p, q, dp, dq] of [[a, b, da, db], [b, c, db, dc], [c, a, dc, da]]) {
        if ((dp > 0) !== (dq > 0)) { const f = dp / (dp - dq); nokta.push(px[p] + (px[q] - px[p]) * f, -L * E + 0.04 * UC.gen / 100, pz[p] + (pz[q] - pz[p]) * f); }
      }
      if (nokta.length === 6) seg.push(...nokta);
    }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.BufferAttribute(new Float32Array(seg), 3));
  const l = new THREE.LineSegments(g, new THREE.LineBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.75 }));
  l.visible = UC.kontur;
  UC.sahne.add(l); UC.obj.kontur = l; UC.konturAdim = adim;
  UC.kirli = true;
}
function ucEfsane() {
  const e = $("#ucEfsane"), v = UC.veri;
  if (!v) { e.innerHTML = ""; return; }
  const { min, max } = v.ozet;
  const grad = l => `linear-gradient(90deg, ${l.join(",")})`;
  if (UC.mod === "derinlik") e.innerHTML = `<b>${t("Derinlik")} (${birim()})</b><div class="skala" style="background:${grad(D.veri.renk || UC_RAMPA.derinlik)}"></div><div class="skala-et"><span>${nf(uzc(min), 1)}</span><span>${nf(uzc(max), 1)}</span></div><small>${t("Kontur aralığı")}: ${nf(uzc(UC.konturAdim), 2)} ${birim()}</small>`;
  else if (UC.mod === "egim") e.innerHTML = `<b>${t("Dip eğimi")} (°)</b><div class="skala" style="background:${grad(UC_RAMPA.egim)}"></div><div class="skala-et"><span>0</span><span>25+</span></div>`;
  else if (UC.mod === "zemin") e.innerHTML = `<b>${t("Zemin sınıfları")} <span class="ince">(${t("göreli")})</span></b>` + (D.veri.kz?.siniflar || []).map(s => `<div class="sinif"><i style="background:${s.renk}"></i>${esc(s.ad)}</div>`).join("");
  else e.innerHTML = `<b>${t("Veri kaynağı")}</b><div class="sinif"><i style="background:${UC_KAYNAK[1]}"></i>${t("Ölçüm")}</div><div class="sinif"><i style="background:${UC_KAYNAK[2]}"></i>${t("Tahmin (uydu analizi)")}</div>`;
}
function ucBilgiYaz() {
  const e = $("#ucBilgi"), o = UC.veri?.ozet;
  if (!o) { e.innerHTML = `<span class="ince">${t("Henüz yüzey yok")}</span>`; return; }
  const satir = [
    [t("Alan"), `${nf(o.alan_m2)} m²`], [t("Hacim"), `${nf(o.hacim_m3)} m³`],
    [t("En derin"), uz(o.max, 2)], [t("En sığ"), uz(o.min, 2)], [t("Ortalama"), uz(o.ort, 2)],
    [t("Kapsam"), `${nf(uzc(o.genislik_m), 0)} × ${nf(uzc(o.yukseklik_m), 0)} ${birim()}`],
    [t("Çözünürlük"), `${nf(uzc(UC.veri.h), UC.veri.h < 1 ? 2 : 1)} ${birim()}`],
  ];
  const tahminPay = o.alan_m2 ? Math.round(100 * o.tahmin_alan_m2 / o.alan_m2) : 0;
  e.innerHTML = satir.map(([a, b]) => `<div><span>${esc(a)}</span><b>${esc(b)}</b></div>`).join("") +
    (tahminPay ? `<div class="uc-uyari">${tahminPay > 0 ? `%${tahminPay} ${t("tahmin")}` : ""}</div>` : "");
}

// ------------------------------------------------------------------ denetimler
function ucBagla() {
  $("#ucE").oninput = e => { UC.E = +e.target.value; $("#ucEYazi").textContent = `×${UC.E}`; if (UC.veri) { UC.hedef.y = UC.taban; ucMeshKur(); UC.hedef = new THREE.Vector3(UC.merkez.x, UC.taban, UC.merkez.z); ucKameraGuncelle(); } };
  $("#ucMod").onchange = e => { UC.mod = e.target.value; if (UC.veri) { ucYenidenRenk(); ucEfsane(); } };
  $("#ucKontur").onchange = e => { UC.kontur = e.target.checked; if (UC.obj.kontur) UC.obj.kontur.visible = UC.kontur; UC.kirli = true; };
  $("#ucSu").onchange = e => { UC.su = e.target.checked; if (UC.obj.su) UC.obj.su.visible = UC.su; UC.kirli = true; };
  $("#ucTahmin").onchange = e => { UC.tahmin = e.target.checked; uc3dYukle(false); };
  $("#ucAdim").onchange = e => { UC.adim = +e.target.value; uc3dYukle(false); };
  $$("#ucKip button").forEach(b => b.onclick = () => { UC.kip = b.dataset.k; $$("#ucKip button").forEach(x => x.classList.toggle("aktif", x === b)); });
  $("#ucAlanSec").onclick = ucAlanSec;
  $("#ucAlanTemizle").onclick = () => { D.alan3d = null; ucAlanKaydet(); alanKatmaniCiz(); ucAlanYazi(); uc3dYukle(true); };
  $$("#ucGorunum button").forEach(b => b.onclick = () => ucGorunum(b.dataset.g));
  $("#ucPng").onclick = () => ucDisari("png");
  $("#ucObj").onclick = () => ucDisari("obj");
  $("#ucStl").onclick = () => ucDisari("stl");
  $("#ucYardim").onclick = () => yardimAc("uc_boyut");
}
function ucYenidenRenk() {
  const m = UC.obj.yuzey, v = UC.veri;
  if (!m || !v) return;
  const col = m.geometry.attributes.color, { min, max } = v.ozet;
  for (let q = 0; q < UC.hu.length; q++) {
    const rgb = ucRenkSec(UC.mod, UC.hu[q], UC.dep[q], min, max, v, UC.egim);
    col.setXYZ(q, rgb[0], rgb[1], rgb[2]);
  }
  col.needsUpdate = true;
  if (UC.obj.duvar) {
    const wc = UC.obj.duvar.geometry.attributes.color;
    UC.sinir.forEach(([a, b], j) => {
      const o = j * 4;
      for (const [k, q] of [[0, a], [2, b]]) wc.setXYZ(o + k, col.getX(q) * 0.55, col.getY(q) * 0.55, col.getZ(q) * 0.55);
    });
    wc.needsUpdate = true;
  }
  UC.kirli = true;
}

// ------------------------------------------------------------------ haritadan alan secimi
function ucAlanSec() {
  if (!D.harita) return;
  sekmeAc("harita");
  setTimeout(() => aracSec("alan3d"), 120);
}
function ucAlanKaydet() {
  try {
    if (D.alan3d) localStorage.setItem("bahr_alan3d_" + D.pid, JSON.stringify(D.alan3d)); else localStorage.removeItem("bahr_alan3d_" + D.pid);
  } catch { /* yok */ }
}
function ucAlanYukle() {
  try { D.alan3d = JSON.parse(localStorage.getItem("bahr_alan3d_" + D.pid) || "null"); } catch { D.alan3d = null; }
}
function alanKatmaniCiz() {
  if (!D.harita) return;
  if (D.alanKatman) { D.harita.removeLayer(D.alanKatman); D.alanKatman = null; }
  if (!D.alan3d) return;
  D.alanKatman = L.polygon(D.alan3d.noktalar, { color: "#22d3ee", weight: 2.2, dashArray: "7 5", fillColor: "#22d3ee", fillOpacity: 0.08, interactive: false })
    .bindTooltip(t("3B alanı"), { permanent: true, direction: "center", className: "olcu-etiket" }).addTo(D.harita);
}
function ucAlanSecildi(noktalar, tip) {
  D.alan3d = { tip, noktalar: noktalar.map(p => [+p.lat.toFixed(7), +p.lng.toFixed(7)]) };
  ucAlanKaydet(); alanKatmaniCiz(); ucAlanYazi();
  UC.veri = null;
  sekmeAc("3d");
  uc3dYukle(true);
}

// ------------------------------------------------------------------ disa aktarma
function ucKati() {
  // kapali kati: yuzey + yan duvar + taban; z yukari, y kuzey (STL / OBJ), taban z = 0
  const { tri, px, pz, dep, E, sinir } = UC, fy = UC.zemin_y;
  const T = [];
  const P = (q, taban) => [px[q], -pz[q], (taban ? fy : -dep[q] * E) - fy];
  for (let i = 0; i < tri.length; i += 3) {
    T.push([P(tri[i], 0), P(tri[i + 1], 0), P(tri[i + 2], 0)]);
    T.push([P(tri[i], 1), P(tri[i + 2], 1), P(tri[i + 1], 1)]);                   // taban: ters sarim
  }
  for (const [a, b] of sinir) { T.push([P(a, 0), P(a, 1), P(b, 0)]); T.push([P(b, 0), P(a, 1), P(b, 1)]); }
  return T;
}
function ucStl(T) {
  const buf = new ArrayBuffer(84 + T.length * 50), dv = new DataView(buf);
  const baslik = "BAHR SONARVIEW 3D topography"; for (let i = 0; i < baslik.length; i++) dv.setUint8(i, baslik.charCodeAt(i));
  dv.setUint32(80, T.length, true);
  T.forEach((t3, i) => {
    const o = 84 + i * 50, [a, b, c] = t3;
    const u = [b[0] - a[0], b[1] - a[1], b[2] - a[2]], w = [c[0] - a[0], c[1] - a[1], c[2] - a[2]];
    let n = [u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2], u[0] * w[1] - u[1] * w[0]];
    const l = Math.hypot(...n) || 1; n = n.map(x => x / l);
    [...n, ...a, ...b, ...c].forEach((f, k) => dv.setFloat32(o + k * 4, f, true));
    dv.setUint16(o + 48, 0, true);
  });
  return new Blob([buf], { type: "model/stl" });
}
function ucObj(T) {
  const harita = new Map(), v = [], f = [];
  const no = p => { const k = `${p[0].toFixed(3)} ${p[1].toFixed(3)} ${p[2].toFixed(3)}`; let i = harita.get(k); if (!i) { v.push(`v ${k}`); i = v.length; harita.set(k, i); } return i; };
  for (const [a, b, c] of T) f.push(`f ${no(a)} ${no(b)} ${no(c)}`);
  return new Blob([`# BAHR SONARVIEW 3B topografya (metre; z yukari, y kuzey; dikey buyutme x${UC.E})\no topografya\n${v.join("\n")}\n${f.join("\n")}\n`], { type: "text/plain" });
}
async function ucDisari(tur) {
  if (!UC.veri || !UC.tri) { bildir(t("Önce bir 3B yüzey oluşturun"), true); return; }
  try {
    let blob;
    const ad = `topografya3b_x${UC.E}`;
    if (tur === "png") {
      UC.r.render(UC.sahne, UC.kam);
      const src = UC.r.domElement, c = document.createElement("canvas");
      c.width = src.width; c.height = src.height;
      const g = c.getContext("2d"), gr = g.createLinearGradient(0, 0, 0, c.height);
      gr.addColorStop(0, "#0e2440"); gr.addColorStop(1, "#050a14");
      g.fillStyle = gr; g.fillRect(0, 0, c.width, c.height);
      g.drawImage(src, 0, 0);
      g.fillStyle = "rgba(255,255,255,.75)"; g.font = `${Math.round(c.height / 38)}px Segoe UI, sans-serif`;
      const o = UC.veri.ozet;
      g.fillText(`${D.proje?.ad || "BAHR SONARVIEW"} · ${nf(o.alan_m2)} m² · ${nf(o.hacim_m3)} m³ · ${t("dikey büyütme")} ×${UC.E}`, c.height / 40, c.height - c.height / 40);
      blob = await new Promise(r => c.toBlob(r, "image/png"));
    } else {
      const T = ucKati();
      blob = tur === "stl" ? ucStl(T) : ucObj(T);
    }
    const r = await fetch(purl(`3b-kaydet?ad=${encodeURIComponent(`${ad}.${tur}`)}`), { method: "POST", body: blob });
    if (!r.ok) throw new Error((await r.json()).detail || "Kaydedilemedi");
    const { yol } = await r.json();
    if (masaustu()) yerelKaydet(yol); else indir(purl(`dosya/${yol}?indir=1`));
  } catch (e) { bildir(e.message, true); }
}
