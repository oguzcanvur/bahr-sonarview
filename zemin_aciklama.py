"""Zemin tipinin nasil belirlendigini anlatan aciklamali sonar gorselleri.

Her zemin sinifindan bir numune noktasi secilir; o noktanin ham sonar kesiti ve
dibe hizalanmis yanki egrisi, uc olcunun (sertlik, penetrasyon, sonumlenme)
nereden alindigi isaretlenerek cizilir.

Cikti: cozumleme/aciklama/Z1..Z3_*.png, Z4_karsilastirma.png
Kullanim:  .venv\\Scripts\\python zemin_aciklama.py   (once zemin.py ve numune.py)
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

RSD = "Sonar000.RSD"
OUT = "cozumleme/aciklama"
ZREL = np.arange(-0.8, 2.5, 0.01)
YARIM = 160                       # kesitte noktanin iki yanindaki ping sayisi (~6 sn)
os.makedirs(OUT, exist_ok=True)

SECIM = [("CAMUR-3", "Yumuşak çamur birikintisi", "#8c510a", "Z1_yumusak_camur.png"),
         ("SILT-2", "Orta: silt / ince çamur", "#c9a64f", "Z2_orta_silt.png"),
         ("SERT-2", "Daha sıkı / sert zemin", "#35978f", "Z3_sert_zemin.png")]

# ------------------------------------------------------------------ veri
d = pd.read_csv("cozumleme/meta/B001_ds_hifreq_meta.csv")
has = d["inst_dep_m"].notna()
seg = (has.astype(int).diff() != 0).cumsum()
d = d[has & (has.groupby(seg).transform("sum") >= 1000)].reset_index(drop=True)
z = np.load("cozumleme/zemin/_ping_oznitelik_onbellek.npz")
for k in ["bottom", "peak", "tail", "decay", "noise"]:
    d["f_" + k] = z[k]
prof = z["prof"] + z["noise"][:, None]              # mutlak yanki, tabana hizali
d["sert"] = d["f_peak"] + d["f_noise"]
d["pen"] = (d["f_tail"] + d["f_noise"]) - d["sert"]
hiz = d["speed_ms"].where(d["speed_ms"] < 5).rolling(51, center=True, min_periods=5).median()
gecerli = (hiz >= 0.28) & d["f_bottom"].notna()
num = pd.read_csv("cozumleme/zemin/numune_noktalari.csv").set_index("nokta")
kx, ky = 111320 * np.cos(np.radians(d["lat"].mean())), 110574.0
# tum kaydin tipik degerleri (karsilastirma cizgisi icin)
TIP = {k: d.loc[gecerli, k].median() for k in ["sert", "pen", "f_decay"]}


def ping_sec(nokta):
    r = num.loc[nokta]
    dist = np.hypot((d["lon"] - r["boylam"]) * kx, (d["lat"] - r["enlem"]) * ky)
    return int(dist[gecerli].idxmin())


def ham_kesit(i0, i1, zmax, ny=420):
    grid = np.linspace(0, zmax, ny)
    img = np.full((ny, i1 - i0), np.nan, np.float32)
    with open(RSD, "rb") as f:
        for j, i in enumerate(range(i0, i1)):
            r = d.iloc[i]
            f.seek(int(r["index"]) + int(r["son_offset"]))
            a = np.frombuffer(f.read(int(r["ping_cnt"]) * 2), "<u2").astype(np.float32)
            zz = np.linspace(r["min_range"], r["max_range"], a.size)
            img[:, j] = np.interp(grid, zz, a, right=np.nan)
    return img


secilen = []
for nokta, ad, renk, dosya in SECIM:
    i = ping_sec(nokta)
    sl = slice(max(0, i - 60), i + 60)
    secilen.append(dict(nokta=nokta, ad=ad, renk=renk, dosya=dosya, i=i, dip=float(d["f_bottom"].iloc[i]),
                        sert=float(d["sert"].iloc[sl].median()), pen=float(d["pen"].iloc[sl].median()),
                        dec=float(d["f_decay"].iloc[sl].median()),
                        egri=np.nanmean(prof[sl], 0)))

# ortak renk olcegi
ZMAX = max(s["dip"] for s in secilen) + 1.7
kesitler = {s["nokta"]: ham_kesit(s["i"] - YARIM, s["i"] + YARIM, ZMAX) for s in secilen}
hepsi = np.concatenate([k[np.isfinite(k)].ravel() for k in kesitler.values()])
LO, HI = np.percentile(hepsi, [8, 99.8])


def renkle(img):
    return np.nan_to_num(np.clip((img - LO) / (HI - LO), 0, 1) ** 1.6, nan=0.0)   # menzil disi: koyu


def kiyas(v, tip, yuksek, dusuk):
    return yuksek if v > tip else dusuk


# ------------------------------------------------------------------ her sinif icin bir gorsel
for s in secilen:
    fig = plt.figure(figsize=(15, 6.6))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.35, 1], wspace=0.16)
    ax = fig.add_subplot(gs[0])
    img = kesitler[s["nokta"]]
    ax.imshow(renkle(img), aspect="auto", cmap="copper", vmin=0, vmax=1,
              extent=[-YARIM / 26, YARIM / 26, ZMAX, 0], interpolation="bilinear")
    b = s["dip"]
    # olcum bantlari
    ax.add_patch(Rectangle((-YARIM / 26, b), 2 * YARIM / 26, 0.15, fc="#22d3ee", alpha=0.22, ec="#22d3ee", lw=1))
    ax.add_patch(Rectangle((-YARIM / 26, b + 0.15), 2 * YARIM / 26, 0.45, fc="#a78bfa", alpha=0.16, ec="#a78bfa", lw=1, ls="--"))
    ax.axhline(b, color="#22d3ee", lw=1.2)
    ax.axhline(b + 1.5, color="#fbbf24", lw=1, ls=":")
    ax.axvline(0, color="white", lw=0.8, ls="--", alpha=0.7)
    kw = dict(color="white", fontsize=10, weight="bold", va="center",
              bbox=dict(boxstyle="round,pad=0.25", fc="#000", alpha=0.55, ec="none"))
    ax.text(YARIM / 26 * 0.98, b - 0.12, "dip yüzeyi", ha="right", **kw)
    ax.text(-YARIM / 26 * 0.97, b + 0.075, "① 0–15 cm: dip yankısı → SERTLİK", ha="left", **kw)
    ax.text(-YARIM / 26 * 0.97, b + 0.38, "② 15–60 cm: kuyruk → PENETRASYON", ha="left", **kw)
    ax.text(-YARIM / 26 * 0.97, b + 1.5 - 0.1, "③ 1,5 m boyunca azalma hızı → SÖNÜMLENME", ha="left", **kw)
    ax.text(-YARIM / 26 * 0.97, 0.25, "su", ha="left", color="white", fontsize=10, alpha=0.8)
    ax.set_xlabel("saniye (0 = numune noktası)")
    ax.set_ylabel("derinlik (m)")
    ax.set_title(f"Ham sonar kesiti — {s['nokta']} (dip {b:.2f} m)", fontsize=11, loc="left")

    # yanki egrisi
    ax2 = fig.add_subplot(gs[1])
    m = (ZREL >= -0.3) & (ZREL <= 1.6)
    for o in secilen:
        if o is not s:
            ax2.plot(o["egri"][m], ZREL[m], color=o["renk"], lw=1, alpha=0.35)
    ax2.plot(s["egri"][m], ZREL[m], color=s["renk"], lw=2.6)
    ax2.axhspan(0, 0.15, color="#22d3ee", alpha=0.15)
    ax2.axhspan(0.15, 0.60, color="#a78bfa", alpha=0.12)
    ax2.axhline(0, color="#22d3ee", lw=1)
    # 1) tepe
    mm = (ZREL >= 0) & (ZREL <= 0.15)
    zt = ZREL[mm][np.nanargmax(s["egri"][mm])]
    ax2.plot(s["sert"], zt, "o", color=s["renk"], mec="k", ms=9, zorder=5)
    ax2.annotate(f"① sertlik\n{s['sert']:,.0f}".replace(",", "."), (s["sert"], zt), xytext=(12, -18),
                 textcoords="offset points", fontsize=9.5, weight="bold")
    # 2) kuyruk ortalamasi
    kuy = s["sert"] + s["pen"]
    ax2.plot([kuy, kuy], [0.15, 0.60], color=s["renk"], lw=3)
    ax2.annotate(f"② kuyruk ortalaması\npenetrasyon = kuyruk − tepe\n= {s['pen']:+,.0f}".replace(",", "."),
                 (kuy, 0.45), xytext=(12, 0), textcoords="offset points", fontsize=9.5, weight="bold", va="center")
    # 3) sonum egimi
    mz = (ZREL >= 0.10) & (ZREL <= 1.50) & np.isfinite(s["egri"])
    p = np.polyfit(ZREL[mz], s["egri"][mz], 1)
    zz = np.array([0.10, 1.50])
    ax2.plot(np.polyval(p, zz), zz, color="k", lw=1.6, ls="--")
    ax2.annotate(f"③ sönümlenme\n{-p[0]:,.0f} birim/m".replace(",", "."), (np.polyval(p, 1.2), 1.2), xytext=(-110, 6),
                 textcoords="offset points", fontsize=9.5, weight="bold")
    ax2.set_ylim(1.6, -0.3)
    ax2.set_xlabel("yankı şiddeti (ham)")
    ax2.set_ylabel("dibe göre derinlik (m)  ·  0 = dip yüzeyi")
    ax2.set_title("Yankı eğrisi (120 ping ortalaması)  — soluk: diğer iki sınıf", fontsize=11, loc="left")
    ax2.grid(alpha=0.25)

    yorum = (f"Sertlik {kiyas(s['sert'], TIP['sert'], 'yüksek', 'düşük')} · "
             f"Penetrasyon {kiyas(s['pen'], TIP['pen'], 'yüksek', 'düşük')} · "
             f"Sönümlenme {kiyas(s['dec'], TIP['f_decay'], 'hızlı', 'yavaş')}")
    fig.suptitle(f"{s['ad']}   ({yorum}; gölün ortancasına göre)", fontsize=13.5, weight="bold",
                 color=s["renk"], x=0.01, ha="left")
    yol = os.path.join(OUT, s["dosya"])
    if os.path.exists(yol):
        os.remove(yol)
    fig.savefig(yol, dpi=130, bbox_inches="tight")
    plt.close(fig)
    print("->", yol, {k: round(v) for k, v in s.items() if k in ("sert", "pen", "dec")})

# ------------------------------------------------------------------ karsilastirma: uc egri ust uste
fig, axs = plt.subplots(1, 2, figsize=(14, 5.6), gridspec_kw=dict(width_ratios=[1.3, 1]))
m = (ZREL >= -0.3) & (ZREL <= 1.6)
for s in secilen:
    axs[0].plot(s["egri"][m], ZREL[m], color=s["renk"], lw=2.4, label=f"{s['ad']} ({s['nokta']})")
axs[0].axhspan(0, 0.15, color="#22d3ee", alpha=0.15)
axs[0].axhspan(0.15, 0.60, color="#a78bfa", alpha=0.12)
axs[0].axhline(0, color="#22d3ee", lw=1)
axs[0].set_ylim(1.6, -0.3)
axs[0].set_xlabel("yankı şiddeti (ham)"); axs[0].set_ylabel("dibe göre derinlik (m)")
axs[0].legend(loc="lower left", fontsize=9.5); axs[0].grid(alpha=0.25)
axs[0].set_title("Üç zeminin yankı eğrisi üst üste", loc="left")
etik = ["① Sertlik\n(dip yankısı)", "② Penetrasyon\n(kuyruk − tepe)", "③ Sönümlenme\n(birim / m)"]
x = np.arange(3)
for j, s in enumerate(secilen):
    v = [s["sert"] - TIP["sert"], s["pen"] - TIP["pen"], s["dec"] - TIP["f_decay"]]
    olc = [abs(d.loc[gecerli, "sert"] - TIP["sert"]).median(), abs(d.loc[gecerli, "pen"] - TIP["pen"]).median(),
           abs(d.loc[gecerli, "f_decay"] - TIP["f_decay"]).median()]
    axs[1].bar(x + (j - 1) * 0.26, np.array(v) / np.array(olc), width=0.25, color=s["renk"], label=s["ad"])
axs[1].axhline(0, color="k", lw=0.8)
axs[1].set_xticks(x, etik)
axs[1].set_ylabel("gölün ortancasından sapma (tipik sapma birimi)")
axs[1].set_title("Üç ölçü: hangisi ortalamanın üstünde / altında", loc="left")
axs[1].grid(axis="y", alpha=0.25)
fig.tight_layout()
yol = os.path.join(OUT, "Z4_karsilastirma.png")
if os.path.exists(yol):
    os.remove(yol)
fig.savefig(yol, dpi=130)
plt.close(fig)
print("->", yol)

# ------------------------------------------------------------------ Z5: genlik - zaman (A-tarama) gorunumu
C_SES = 1455.0                                       # 12 C tatli su (m/s)
fig, ax = plt.subplots(figsize=(13, 5.8))
m = (ZREL >= -0.25) & (ZREL <= 1.5)
t_ms = 2 * ZREL[m] / C_SES * 1000                    # dip yankisinin gelisine gore gidis-donus suresi
for s in secilen:
    ax.plot(t_ms, s["egri"][m], color=s["renk"], lw=2.4, label=f"{s['ad']} ({s['nokta']})")
t15, t60, t150 = (2 * np.array([0.15, 0.60, 1.50]) / C_SES * 1000)
ax.axvspan(0, t15, color="#22d3ee", alpha=0.15)
ax.axvspan(t15, t60, color="#a78bfa", alpha=0.12)
ax.axvline(0, color="#22d3ee", lw=1.2)
ust = max(s["egri"][m].max() for s in secilen)
ax.text(t15 / 2, ust * 1.035, "① tepe genlik\n→ SERTLİK", ha="center", fontsize=10, weight="bold")
ax.text((t15 + t60) / 2, ust * 1.035, "② kuyruk genliği − tepe genlik\n→ PENETRASYON", ha="center", fontsize=10, weight="bold")
ax.text((t60 + t150) / 2 + 0.3, ust * 1.035, "③ genliğin zamanla düşme hızı → SÖNÜMLENME", ha="center", fontsize=10, weight="bold")
ax.text(-0.17, ust * 0.93, "su:\ndönen ses az\n(düşük genlik)", ha="center", fontsize=9.5, color="#555")
ax.annotate("ses dibe çarptı", (0, ust * 0.70), xytext=(0.5, ust * 0.58), fontsize=9.5,
            arrowprops=dict(arrowstyle="->", color="#333"))
ax.set_ylim(ax.get_ylim()[0], ust * 1.12)
ax.set_xlabel("dip yankısından sonra geçen süre (milisaniye, gidiş-dönüş)  ·  1 ms ≈ 73 cm dip altı")
ax.set_ylabel("dönen sesin genliği (cihazın ham, logaritmik birimi)")
ax.set_title("Genlik – zaman eğrisi: her ping'de dipten dönen ses (120 ping ortalaması)", loc="left", fontsize=12)
ax.legend(loc="lower left", fontsize=10)
ax.grid(alpha=0.25)
fig.tight_layout()
yol = os.path.join(OUT, "Z5_genlik_zaman.png")
if os.path.exists(yol):
    os.remove(yol)
fig.savefig(yol, dpi=130)
plt.close(fig)
print("->", yol)
