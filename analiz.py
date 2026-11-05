"""Garmin RSD sonar kaydindan grafik ve goruntu uretir.

Once PINGVerter ile cozulmus metadata gerekir (cozumleme/meta/B001_ds_hifreq_meta.csv).
Kullanim:  .venv\\Scripts\\python analiz.py
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

RSD = "Sonar000.RSD"
META = "cozumleme/meta/B001_ds_hifreq_meta.csv"
OUT = "cozumleme/grafikler"
os.makedirs(OUT, exist_ok=True)

def _kaydet(fig, yol, dpi):
    """Windows'ta mevcut PNG uzerine yazma bazen Errno 22 verdiginden once eskisini sil."""
    if os.path.exists(yol):
        os.remove(yol)
    fig.savefig(yol, dpi=dpi)


d = pd.read_csv(META)
d["dt"] = pd.to_datetime(d["date"] + " " + d["time"], format="ISO8601")
# GPS sicramalarini ele (gercekci olmayan hiz)
d.loc[d["speed_ms"] > 5, "speed_ms"] = np.nan


def read_ping(f, row):
    f.seek(int(row["index"]) + int(row["son_offset"]))
    n = int(row["ping_cnt"])
    a = np.frombuffer(f.read(n * 2), dtype="<u2")
    return a if a.size == n else None


# ---------- 1) Echogram (tum kayit + yakin plan) ----------
def echogram(sub, depth_max, nbins, fname, title, step=1):
    sub = sub.iloc[::step]
    grid = np.linspace(0, depth_max, nbins)
    img = np.full((nbins, len(sub)), np.nan, dtype=np.float32)
    with open(RSD, "rb") as f:
        for j, (_, r) in enumerate(sub.iterrows()):
            a = read_ping(f, r)
            if a is None:
                continue
            z = np.linspace(r["min_range"], r["max_range"], a.size)
            img[:, j] = np.interp(grid, z, a.astype(np.float32), right=np.nan)
    lo, hi = np.nanpercentile(img, [2, 99.5])
    fig, ax = plt.subplots(figsize=(16, 6))
    t0 = sub["time_s"].iloc[0] / 60
    t1 = sub["time_s"].iloc[-1] / 60
    ax.imshow(img, aspect="auto", cmap="copper", vmin=lo, vmax=hi,
              extent=[t0, t1, depth_max, 0], interpolation="nearest")
    ax.plot(sub["time_s"] / 60, sub["inst_dep_m"], color="cyan", lw=0.6,
            alpha=0.8, label="Cihazin olctugu derinlik")
    ax.set_xlabel("Kayit basindan itibaren sure (dk)")
    ax.set_ylabel("Derinlik (m)")
    ax.set_title(title)
    ax.legend(loc="lower right")
    fig.tight_layout()
    _kaydet(fig, os.path.join(OUT, fname), 130)
    plt.close(fig)


valid = d[d["max_range"] < 50]  # baslangictaki 670 m'lik ayar ping'lerini atla
echogram(valid, 8, 600, "1_echogram_tum_kayit.png",
         "Sonar goruntusu (echogram) - tum kayit", step=max(1, len(valid) // 4000))
mid = len(valid) // 2
echogram(valid.iloc[mid:mid + 3000], 6, 700, "2_echogram_yakin_plan.png",
         "Sonar goruntusu - yakin plan (~2 dakika, her ping)")

# ---------- 2) Rota haritasi (derinlige gore renkli) ----------
dd = d.dropna(subset=["inst_dep_m"])
fig, ax = plt.subplots(figsize=(9, 9))
sc = ax.scatter(dd["e"] - dd["e"].min(), dd["n"] - dd["n"].min(),
                c=dd["inst_dep_m"], cmap="viridis_r", s=2)
fig.colorbar(sc, ax=ax, label="Derinlik (m)")
ax.set_aspect("equal")
ax.set_xlabel("Dogu (m, UTM)")
ax.set_ylabel("Kuzey (m, UTM)")
ax.set_title("Tekne rotasi - renk: derinlik")
fig.tight_layout()
_kaydet(fig, os.path.join(OUT, "3_rota_derinlik_haritasi.png"), 130)
plt.close(fig)

# ---------- 3) Zaman serileri ----------
fig, axs = plt.subplots(3, 1, figsize=(14, 9), sharex=True)
m = d["time_s"] / 60
axs[0].plot(m, d["inst_dep_m"], lw=0.5)
axs[0].invert_yaxis()
axs[0].set_ylabel("Derinlik (m)")
axs[1].plot(m, d["speed_ms"].rolling(200, min_periods=1).median() * 3.6, lw=0.8, color="tab:orange")
axs[1].set_ylabel("Hiz (km/sa)")
axs[2].plot(m, d["tempC"], lw=0.8, color="tab:red")
axs[2].set_ylabel("Su sicakligi (C)")
axs[2].set_xlabel("Sure (dk)")
axs[0].set_title("Derinlik, hiz ve su sicakligi")
fig.tight_layout()
_kaydet(fig, os.path.join(OUT, "4_zaman_serileri.png"), 130)
plt.close(fig)

# ---------- 4) CSV ----------
cols = ["dt", "time_s", "lat", "lon", "inst_dep_m", "speed_ms", "instr_heading", "tempC", "max_range", "gain"]
d[cols].to_csv(os.path.join(OUT, "ping_ozet.csv"), index=False)
print("Bitti ->", OUT)
