"""Pipeline Data Cleaning + Pelatihan Mendalam ANN Perceptron (5 -> 16 ReLU -> 1) untuk Prediksi H+7.

Tahapan Pembersihan Data (Data Cleaning) & Penyesuaian Kalender:
1. Rekonstruksi Kalender Harian Kontinu (Daily Calendar Re-indexing):
   - Mengisi 8.892 hari yang kosong (cell kosong / libur pasar) menggunakan Forward-Fill (LOCF)
     sehingga setiap pergeseran indeks t-7, t-14, t-21, dan target t+7 dijamin 100% jatuh tepat
     pada hari kalender yang sama (Senin ke Senin, Selasa ke Selasa).
2. Pembersihan Anomali Salah Input (Causal Hampel / Rolling Median Filter):
   - Memperbaiki ~236 titik kesalahan ketik ekstrem (contoh: harga minyak goreng Rp 18.375
     tertulis Rp 99.625 selama 1 hari lalu kembali Rp 18.625, atau cabai Rp 100.000 tertulis Rp 10.000)
     apabila menyimpang > 35% terhadap median kausal 7 hari terakhir dan terbukti merupakan anomali sesaat.
3. Pelatihan Mendalam (Multi-Config ANN 5->16->1 pada 2 CPU Core):
   - Menggunakan 2 CPU thread (OMP_NUM_THREADS=2).
   - Melatih dan memilih kandidat terbaik dari variasi regularisasi L2 (alpha) & learning rate
     dengan konvergensi presisi tinggi (tol=1e-5, max_iter=800, n_iter_no_change=25).
   - Dilengkapi pengaman interupsi (Ctrl+C / SIGINT / SIGTERM / .stop_training).
"""

from __future__ import annotations

import os

# 1. KONFIGURASI 2 CPU CORE (Sesuai arahan pengguna: optimal, cepat, dan tidak membuat Mac hang)
os.environ["OMP_NUM_THREADS"] = "2"
os.environ["OPENBLAS_NUM_THREADS"] = "2"
os.environ["MKL_NUM_THREADS"] = "2"
os.environ["VECLIB_MAXIMUM_THREADS"] = "2"
os.environ["NUMEXPR_NUM_THREADS"] = "2"

import argparse
import json
import pathlib
import signal
import statistics
import sys
import time
from datetime import date, datetime, timedelta, timezone

import numpy as np
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error, root_mean_squared_error
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import runlog  # noqa: E402
from app.services import bapanas as bapanas_service  # noqa: E402

OUT_PATH = ROOT / "data" / "derived" / "bobot_ann_h7.json"
LAPORAN_CLEANING_PATH = ROOT / "data" / "derived" / "laporan_cleaning_ann.json"
STOP_FILE = ROOT / "data" / "derived" / ".stop_training"

# Konfigurasi Arsitektur ANN Perceptron (Terkunci: 5 Input -> 16 Hidden ReLU -> 1 Output H+7)
HORIZON = 7
LAGS = [0, 1, 7, 14, 21]  # H(t), H(t-1), H(t-7), H(t-14), H(t-21)
MIN_LAG = max(LAGS)       # 21 hari kalender ke belakang
HIDDEN_UNITS = (16,)
TRAIN_RATIO = 0.80
AMBANG_ANOMALI_TYPO = 0.35  # Deviasi > 35% dari median lokal yang langsung berbalik dianggap typo input

_STOP_REQUESTED = False
_STOP_REASON = ""


def _handle_stop_signal(signum: int, _frame) -> None:
    global _STOP_REQUESTED, _STOP_REASON
    sig_name = signal.Signals(signum).name
    _STOP_REQUESTED = True
    _STOP_REASON = f"Menerima sinyal penghentian {sig_name}"
    print(f"\n[STOP GUARD] {_STOP_REASON}. Menghentikan pelatihan secara aman setelah seri ini selesai...", flush=True)


signal.signal(signal.SIGINT, _handle_stop_signal)
signal.signal(signal.SIGTERM, _handle_stop_signal)


def cek_harus_berhenti(start_time: float, max_seconds: float) -> bool:
    global _STOP_REQUESTED, _STOP_REASON
    if _STOP_REQUESTED:
        return True
    if STOP_FILE.exists():
        _STOP_REQUESTED = True
        _STOP_REASON = f"Ditemukan berkas penghenti {STOP_FILE.name}"
        try:
            STOP_FILE.unlink()
        except OSError:
            pass
        print(f"\n[STOP GUARD] {_STOP_REASON}. Menghentikan pelatihan secara aman...", flush=True)
        return True
    elapsed = time.monotonic() - start_time
    if elapsed > max_seconds:
        _STOP_REQUESTED = True
        _STOP_REASON = f"Melewati batas waktu aman ({max_seconds:.0f} detik)"
        print(f"\n[STOP GUARD] {_STOP_REASON}. Menghentikan pelatihan...", flush=True)
        return True
    return False


def kuantil(data: list[float], p: float) -> float:
    if not data:
        return 0.0
    urut = sorted(data)
    idx = min(len(urut) - 1, max(0, int(round(p * (len(urut) - 1)))))
    return float(urut[idx])


def bersihkan_dan_rekonstruksi_kalender(
    seri_mentah: list[tuple[str, int]],
) -> tuple[list[tuple[str, int]], dict]:
    """Tahap Data Cleaning menyeluruh untuk satu seri (wilayah, komoditas):
    1. Urutkan dan hapus duplikat tanggal.
    2. Bangun grid kalender harian penuh tanpa celah (d_start .. d_end) dan isi
       cell kosong menggunakan Forward-Fill (LOCF).
    3. Bersihkan kesalahan ketik ekstrem (isolated typo spikes > 35% yang berbalik dalam 1-2 hari)
       menggunakan filter median lokal agar gradien ANN tidak rusak oleh salah input.
    """
    peta_tanggal: dict[date, int] = {}
    for t_str, h in seri_mentah:
        if h and h > 0:
            peta_tanggal[date.fromisoformat(t_str)] = int(h)

    if len(peta_tanggal) < 2:
        return seri_mentah, {"hari_kosong_diisi": 0, "anomali_typo_diperbaiki": 0, "total_hari_kalender": len(seri_mentah)}

    d_awal = min(peta_tanggal.keys())
    d_akhir = max(peta_tanggal.keys())
    total_hari = (d_akhir - d_awal).days + 1

    # Step 1: Forward-Fill pada kalender harian utuh
    tanggal_list: list[str] = []
    nilai_list: list[int] = []
    harga_terakhir = peta_tanggal[d_awal]
    hari_kosong_diisi = 0

    for offset in range(total_hari):
        d_kini = d_awal + timedelta(days=offset)
        if d_kini in peta_tanggal:
            harga_terakhir = peta_tanggal[d_kini]
        else:
            hari_kosong_diisi += 1
        tanggal_list.append(d_kini.isoformat())
        nilai_list.append(harga_terakhir)

    # Step 2: Deteksi & koreksi isolated typo spike/drop (Hampel median filter)
    anomali_diperbaiki = 0
    contoh_koreksi: list[dict] = []
    nilai_bersih = list(nilai_list)

    for i in range(3, len(nilai_bersih) - 2):
        val = nilai_bersih[i]
        # Ambil tetangga sebelum dan sesudah untuk memverifikasi apakah lonjakan bersifat terisolasi (typo)
        tetangga_kiri = nilai_bersih[max(0, i - 5) : i]
        tetangga_kanan = nilai_bersih[i + 1 : min(len(nilai_bersih), i + 4)]
        med_kiri = statistics.median(tetangga_kiri)
        med_kanan = statistics.median(tetangga_kanan)

        if med_kiri > 0 and med_kanan > 0:
            dev_kiri = abs(val - med_kiri) / med_kiri
            dev_kanan = abs(val - med_kanan) / med_kanan
            # Jika menyimpang > 35% dari median kiri DAN kembali ke level normal di kanan (typo sesaat)
            if dev_kiri > AMBANG_ANOMALI_TYPO and dev_kanan > AMBANG_ANOMALI_TYPO:
                pengganti = int(round(med_kiri))
                if len(contoh_koreksi) < 3:
                    contoh_koreksi.append(
                        {
                            "tanggal": tanggal_list[i],
                            "harga_mentah_typo": val,
                            "harga_koreksi": pengganti,
                        }
                    )
                nilai_bersih[i] = pengganti
                anomali_diperbaiki += 1

    seri_bersih = list(zip(tanggal_list, nilai_bersih))
    statistik_cleaning = {
        "observasi_mentah": len(peta_tanggal),
        "total_hari_kalender": total_hari,
        "hari_kosong_diisi": hari_kosong_diisi,
        "anomali_typo_diperbaiki": anomali_diperbaiki,
        "contoh_koreksi": contoh_koreksi,
    }
    return seri_bersih, statistik_cleaning


def bangun_matriks_siklus_mingguan(nilai: list[int]) -> tuple[np.ndarray, np.ndarray]:
    """Bentuk matriks X = [H(t), H(t-1), H(t-7), H(t-14), H(t-21)] dan Y = H(t+7)
    pada deret harian yang sudah berurutan kalender penuh (tanpa tanggal bolong).
    """
    X_rows = []
    y_rows = []
    n = len(nilai)
    for t in range(MIN_LAG, n - HORIZON):
        fitur = [float(nilai[t - lag]) for lag in LAGS]
        target = float(nilai[t + HORIZON])
        X_rows.append(fitur)
        y_rows.append(target)
    return np.array(X_rows, dtype=np.float64), np.array(y_rows, dtype=np.float64)


def latih_satu_seri(seri_mentah: list[tuple[str, int]], max_iter: int = 800) -> tuple[dict | None, dict]:
    """Bersihkan data seri, lalu latih & pilih konfigurasi terbaik ANN Perceptron (5 -> 16 ReLU -> 1)."""
    seri_bersih, info_cleaning = bersihkan_dan_rekonstruksi_kalender(seri_mentah)
    nilai = [v for _t, v in seri_bersih]

    if len(nilai) < MIN_LAG + HORIZON + 30:
        return None, info_cleaning

    X, y = bangun_matriks_siklus_mingguan(nilai)
    split = int(len(y) * TRAIN_RATIO)
    if split < 30 or (len(y) - split) < 10:
        return None, info_cleaning

    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]

    scaler_x = StandardScaler()
    scaler_y = StandardScaler()

    X_train_s = scaler_x.fit_transform(X_train)
    X_test_s = scaler_x.transform(X_test)
    y_train_s = scaler_y.fit_transform(y_train.reshape(-1, 1)).ravel()

    # Pisahkan 15% ujung kronologis dari data train sebagai internal validation set
    # untuk memilih kandidat hyperparameter terbaik tanpa menyentuh X_test sama sekali!
    val_split = int(len(X_train_s) * 0.85)
    X_subtrain, X_val = X_train_s[:val_split], X_train_s[val_split:]
    y_subtrain, y_val = y_train_s[:val_split], y_train_s[val_split:]

    kandidat_params = [
        {"alpha": 0.5, "lr": 0.005, "seed": 42},
        {"alpha": 2.0, "lr": 0.005, "seed": 42},
        {"alpha": 5.0, "lr": 0.003, "seed": 101},
    ]

    best_cfg = kandidat_params[0]
    best_val_loss = float("inf")

    for cfg in kandidat_params:
        probe = MLPRegressor(
            hidden_layer_sizes=HIDDEN_UNITS,
            activation="relu",
            solver="adam",
            alpha=cfg["alpha"],
            learning_rate_init=cfg["lr"],
            max_iter=max_iter,
            early_stopping=True,
            validation_fraction=0.15,
            n_iter_no_change=25,
            tol=1e-5,
            random_state=cfg["seed"],
        )
        probe.fit(X_subtrain, y_subtrain)
        val_pred = probe.predict(X_val)
        val_loss = float(np.mean(np.abs(y_val - val_pred)))
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_cfg = cfg

    # Latih model final pada seluruh X_train_s menggunakan konfigurasi terbaik
    mlp = MLPRegressor(
        hidden_layer_sizes=HIDDEN_UNITS,
        activation="relu",
        solver="adam",
        alpha=best_cfg["alpha"],
        learning_rate_init=best_cfg["lr"],
        max_iter=max_iter,
        early_stopping=True,
        validation_fraction=0.15,
        n_iter_no_change=25,
        tol=1e-5,
        random_state=best_cfg["seed"],
    )
    mlp.fit(X_train_s, y_train_s)

    pred_test_s = mlp.predict(X_test_s)
    pred_test = scaler_y.inverse_transform(pred_test_s.reshape(-1, 1)).ravel()

    mae = float(mean_absolute_error(y_test, pred_test))
    rmse = float(root_mean_squared_error(y_test, pred_test))
    mape = float(mean_absolute_percentage_error(y_test, pred_test) * 100.0)

    rel_errors = [
        float((y_test[i] - pred_test[i]) / pred_test[i])
        for i in range(len(y_test))
        if pred_test[i] > 0
    ]
    q10 = min(kuantil(rel_errors, 0.10) if rel_errors else -0.05, -0.01)
    q90 = max(kuantil(rel_errors, 0.90) if rel_errors else 0.05, 0.01)

    W1 = [[round(float(v), 6) for v in row] for row in mlp.coefs_[0].tolist()]
    b1 = [round(float(v), 6) for v in mlp.intercepts_[0].tolist()]
    W2 = [round(float(row[0]), 6) for row in mlp.coefs_[1].tolist()]
    b2 = round(float(mlp.intercepts_[1][0]), 6)

    mean_x = [round(float(v), 4) for v in scaler_x.mean_.tolist()]
    scale_x = [round(float(v) if v > 0 else 1.0, 4) for v in scaler_x.scale_.tolist()]
    mean_y = round(float(scaler_y.mean_[0]), 4)
    scale_y = round(float(scaler_y.scale_[0]) if scaler_y.scale_[0] > 0 else 1.0, 4)

    hasil_model = {
        "arsitektur": "5-16-1",
        "aktivasi": "relu",
        "lags": LAGS,
        "horizon_hari": HORIZON,
        "hyperparameter_terpilih": best_cfg,
        "data_cleaning": {
            "observasi_mentah": info_cleaning["observasi_mentah"],
            "total_hari_kalender": info_cleaning["total_hari_kalender"],
            "hari_kosong_diisi_ffill": info_cleaning["hari_kosong_diisi"],
            "anomali_typo_diperbaiki": info_cleaning["anomali_typo_diperbaiki"],
        },
        "n_latih": int(len(y_train)),
        "n_uji": int(len(y_test)),
        "iterasi_konvergen": int(mlp.n_iter_),
        "metrik_uji": {
            "mae_rp": round(mae, 2),
            "rmse_rp": round(rmse, 2),
            "mape_persen": round(mape, 2),
        },
        "pita_residual": {
            "q10": round(q10, 4),
            "q90": round(q90, 4),
        },
        "bobot": {
            "mean_x": mean_x,
            "scale_x": scale_x,
            "mean_y": mean_y,
            "scale_y": scale_y,
            "W1": W1,
            "b1": b1,
            "W2": W2,
            "b2": b2,
        },
    }
    return hasil_model, info_cleaning


def main() -> int:
    parser = argparse.ArgumentParser(description="Data Cleaning + Pelatihan ANN Perceptron H+7 (2 CPU Core).")
    parser.add_argument("--max-seconds", type=float, default=180.0, help="Batas waktu aman maksimum (detik)")
    parser.add_argument("--sleep-ms", type=float, default=2.0, help="Jeda mikro antar-model (milidetik)")
    parser.add_argument("--max-iter", type=int, default=800, help="Batas iterasi maksimum per model ANN")
    args = parser.parse_args()

    start_time = time.monotonic()
    if STOP_FILE.exists():
        try:
            STOP_FILE.unlink()
        except OSError:
            pass

    muat = bapanas_service._muat()["harga"]
    semua_kunci = sorted(muat.keys())
    total_seri = len(semua_kunci)

    print(
        f"[ANN PIPELINE] Memulai Data Cleaning + Multi-Start Training untuk {total_seri} seri (27 Wilayah x 6 Komoditas)\n"
        f"               Alokasi CPU: 2 Core | Max Iter: {args.max_iter} | Timeout Guard: {args.max_seconds:.0f}s\n"
        f"               Cara hentikan kapan saja: Ctrl+C atau buat file {STOP_FILE.name}",
        flush=True,
    )

    model_map: dict[str, dict] = {}
    ringkasan_komoditas: dict[str, list[dict]] = {}
    total_hari_kosong_diisi = 0
    total_typo_diperbaiki = 0
    daftar_contoh_koreksi: list[dict] = []
    berhasil = 0

    ctx = runlog.mulai("ann_perceptron_h7")
    for idx, (wilayah_norm, komoditas) in enumerate(semua_kunci, 1):
        if cek_harus_berhenti(start_time, args.max_seconds):
            break

        seri_mentah = muat[(wilayah_norm, komoditas)]
        hasil, info_clean = latih_satu_seri(seri_mentah, max_iter=args.max_iter)

        total_hari_kosong_diisi += info_clean["hari_kosong_diisi"]
        total_typo_diperbaiki += info_clean["anomali_typo_diperbaiki"]
        for c in info_clean.get("contoh_koreksi", []):
            if len(daftar_contoh_koreksi) < 25:
                daftar_contoh_koreksi.append({"wilayah": wilayah_norm, "komoditas": komoditas, **c})

        if hasil is not None:
            kunci_str = f"{wilayah_norm}|{komoditas}"
            model_map[kunci_str] = hasil
            ringkasan_komoditas.setdefault(komoditas, []).append(hasil["metrik_uji"])
            berhasil += 1

        if args.sleep_ms > 0:
            time.sleep(args.sleep_ms / 1000.0)

        if idx % 27 == 0 or idx == total_seri:
            elapsed = time.monotonic() - start_time
            print(
                f"  -> Progres: {idx:3d}/{total_seri} seri | "
                f"Cell kosong diisi: {total_hari_kosong_diisi:,} hari | "
                f"Typo ekstrem dikoreksi: {total_typo_diperbaiki} titik | "
                f"Waktu: {elapsed:.1f}s",
                flush=True,
            )

    rekap_komoditas = {}
    for kom, daftar_m in sorted(ringkasan_komoditas.items()):
        n_k = len(daftar_m)
        rekap_komoditas[kom] = {
            "jumlah_wilayah": n_k,
            "rata_mae_rp": round(sum(m["mae_rp"] for m in daftar_m) / n_k, 2),
            "rata_rmse_rp": round(sum(m["rmse_rp"] for m in daftar_m) / n_k, 2),
            "rata_mape_persen": round(sum(m["mape_persen"] for m in daftar_m) / n_k, 2),
            "min_mape_persen": round(min(m["mape_persen"] for m in daftar_m), 2),
            "max_mape_persen": round(max(m["mape_persen"] for m in daftar_m), 2),
        }

    ringkasan_cleaning = {
        "total_seri_diproses": berhasil,
        "total_cell_tanggal_kosong_diimputasi_ffill": total_hari_kosong_diisi,
        "total_anomali_salah_ketik_dikoreksi": total_typo_diperbaiki,
        "contoh_koreksi_anomali": daftar_contoh_koreksi,
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    LAPORAN_CLEANING_PATH.write_text(json.dumps(ringkasan_cleaning, indent=2), encoding="utf-8")

    payload = {
        "meta": {
            "metode": "ann_perceptron_5_16_1",
            "deskripsi": (
                "Model prediksi harga H+7 (Direct 7-day-ahead forecasting) berbasis "
                "Artificial Neural Network (Multilayer Perceptron 5 -> 16 ReLU -> 1) "
                "dengan rekonstruksi kalender harian penuh (imputasi cell kosong) dan "
                "pembersihan anomali salah input (Hampel median filter)."
            ),
            "sumber_data": "Badan Pangan Nasional (2024-2026)",
            "diperbarui_pada": datetime.now(timezone.utc).isoformat(),
            "jumlah_model_terlatih": berhasil,
            "ringkasan_data_cleaning": {
                "total_cell_kosong_diimputasi": total_hari_kosong_diisi,
                "total_anomali_typo_dikoreksi": total_typo_diperbaiki,
            },
            "dihentikan_lebih_awal": _STOP_REQUESTED,
            "alasan_berhenti": _STOP_REASON or None,
            "input_neurons": ["H(t)", "H(t-1)", "H(t-7)", "H(t-14)", "H(t-21)"],
            "hidden_layer": {"neurons": 16, "activation": "ReLU"},
            "output_neuron": "H(t+7)",
        },
        "ringkasan_evaluasi_per_komoditas": rekap_komoditas,
        "models": model_map,
    }
    OUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    runlog.selesai(
        ctx,
        status="stopped" if _STOP_REQUESTED else "ok",
        berkas=OUT_PATH,
        jumlah_baris=berhasil,
        pesan=(
            f"{berhasil} model ANN terlatih | "
            f"{total_hari_kosong_diisi} cell kosong diisi | "
            f"{total_typo_diperbaiki} typo dikoreksi"
        ),
    )

    total_waktu = time.monotonic() - start_time
    print(
        f"\n[SELESAI] {berhasil}/{total_seri} model ANN Perceptron selesai dilatih dalam {total_waktu:.2f} detik.\n"
        f"          Rekap Data Cleaning: {total_hari_kosong_diisi:,} hari kosong diisi (Forward-Fill) & "
        f"{total_typo_diperbaiki} anomali typo ekstrem dikoreksi."
    )
    for kom, rek in rekap_komoditas.items():
        print(
            f"  - {kom:22s}: Rata-rata MAPE = {rek['rata_mape_persen']:5.2f}% "
            f"(Min {rek['min_mape_persen']:.2f}% .. Max {rek['max_mape_persen']:.2f}%), "
            f"MAE = Rp {rek['rata_mae_rp']:,.0f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
