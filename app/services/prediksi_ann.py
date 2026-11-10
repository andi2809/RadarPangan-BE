"""Layanan Inferensi Prediksi Harga H+7 Berbasis ANN Perceptron (5 -> 16 ReLU -> 1).

Prinsip:
- Zero-Dependency di Server Produksi (Vercel): membaca matriks bobot dan parameter
  normalisasi dari `data/derived/bobot_ann_h7.json` yang dihasilkan oleh
  `pipeline/prediksi_ann_h7.py`.
- Rekonstruksi Kalender Harian Saat Inferensi: sebelum mengambil titik [H(t), H(t-1), H(t-7), H(t-14), H(t-21)],
  deret waktu direkonstruksi ke kalender harian utuh (mengisi cell tanggal kosong dengan Forward-Fill)
  agar lag t-7, t-14, dan t-21 benar-benar tepat 7, 14, dan 21 hari kalender yang lalu (Senin ke Senin).
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Optional

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
BOBOT_PATH = DATA_DIR / "derived" / "bobot_ann_h7.json"

LAGS = (0, 1, 7, 14, 21)
_ALIAS_KOMODITAS = {"minyakita": "minyak_goreng_kemasan"}


def _wilayah(nama: str) -> str:
    return " ".join(str(nama).lower().replace(".", "").split())


def _kode(komoditas: str) -> str:
    return _ALIAS_KOMODITAS.get(komoditas, komoditas)


@lru_cache(maxsize=1)
def _muat_bobot() -> dict[str, Any]:
    if not BOBOT_PATH.is_file():
        return {"meta": {}, "ringkasan_evaluasi_per_komoditas": {}, "models": {}}
    try:
        return json.loads(BOBOT_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"meta": {}, "ringkasan_evaluasi_per_komoditas": {}, "models": {}}


def _rekonstruksi_kalender_harian(titik: list[tuple[str, int]]) -> list[int]:
    """Pastikan deret waktu harian tidak memiliki tanggal bolong (isi cell kosong dengan Forward-Fill)."""
    peta: dict[date, int] = {}
    urut_mentah: list[int] = []
    for t_str, v in titik:
        if v and v > 0:
            urut_mentah.append(int(v))
            try:
                peta[date.fromisoformat(str(t_str)[:10])] = int(v)
            except ValueError:
                pass
    if len(peta) < 2:
        return urut_mentah

    d_akhir = max(peta.keys())
    # Cukup rekonstruksi 35 hari kalender terakhir untuk kebutuhan lag t-21
    d_mulai = max(min(peta.keys()), d_akhir - timedelta(days=35))

    # Cari nilai awal pada atau sebelum d_mulai
    tanggal_urut = sorted(peta.keys())
    harga_terakhir = peta[tanggal_urut[0]]
    for d in tanggal_urut:
        if d <= d_mulai:
            harga_terakhir = peta[d]
        else:
            break

    span = (d_akhir - d_mulai).days + 1
    hasil_harian: list[int] = []
    for offset in range(span):
        d_kini = d_mulai + timedelta(days=offset)
        if d_kini in peta:
            harga_terakhir = peta[d_kini]
        hasil_harian.append(harga_terakhir)
    return hasil_harian


def _forward_pass_ann(x_lags: list[float], bobot: dict[str, Any]) -> int:
    """Hitung forward-pass jaringan ANN Perceptron (5 -> 16 ReLU -> 1) dengan Python murni."""
    mean_x: list[float] = bobot["mean_x"]
    scale_x: list[float] = bobot["scale_x"]
    mean_y: float = bobot["mean_y"]
    scale_y: float = bobot["scale_y"]
    W1: list[list[float]] = bobot["W1"]
    b1: list[float] = bobot["b1"]
    W2: list[float] = bobot["W2"]
    b2: float = bobot["b2"]

    # 1. Standardisasi Input (5 Neuron)
    x_norm = [
        (x_lags[i] - mean_x[i]) / (scale_x[i] if scale_x[i] != 0 else 1.0)
        for i in range(5)
    ]

    # 2. Hidden Layer (16 Neuron Perceptron dengan fungsi aktivasi ReLU)
    n_hidden = len(b1)
    hidden = [
        max(0.0, sum(x_norm[i] * W1[i][j] for i in range(5)) + b1[j])
        for j in range(n_hidden)
    ]

    # 3. Output Layer (1 Neuron H+7) + Inverse Standardisasi ke Rupiah
    y_norm = sum(hidden[j] * W2[j] for j in range(n_hidden)) + b2
    harga_h7 = y_norm * scale_y + mean_y
    return max(100, round(harga_h7))


def prediksi_h7(
    nama_wilayah: str,
    komoditas: str,
    seri: Iterable[tuple[str, int]],
) -> Optional[dict[str, Any]]:
    """Hitung prediksi harga H+7 (tepat 7 hari kalender ke depan) menggunakan ANN Perceptron."""
    titik = list(seri)
    if len(titik) < 2:
        return None

    kunci = f"{_wilayah(nama_wilayah)}|{_kode(komoditas)}"
    paket = _muat_bobot()
    model_info = paket.get("models", {}).get(kunci)
    if not model_info:
        return None

    nilai_kalender = _rekonstruksi_kalender_harian(titik)
    if len(nilai_kalender) < 2:
        return None

    n = len(nilai_kalender)
    harga_hari_ini = nilai_kalender[-1]

    # Ambil 5 titik lag siklus mingguan tepat pada kalender harian: H(t), H(t-1), H(t-7), H(t-14), H(t-21)
    x_lags = [float(nilai_kalender[max(0, n - 1 - lag)]) for lag in LAGS]

    harga_prediksi = _forward_pass_ann(x_lags, model_info["bobot"])

    pita = model_info.get("pita_residual", {"q10": -0.05, "q90": 0.05})
    q10 = float(pita.get("q10", -0.05))
    q90 = float(pita.get("q90", 0.05))

    batas_bawah = max(100, round(harga_prediksi * (1.0 + q10)))
    batas_atas = max(batas_bawah, round(harga_prediksi * (1.0 + q90)))
    perubahan_persen = (
        round(((harga_prediksi - harga_hari_ini) / harga_hari_ini) * 100.0, 2)
        if harga_hari_ini > 0
        else 0.0
    )

    return {
        "harga_prediksi_h7_rp": harga_prediksi,
        "batas_bawah_h7_rp": batas_bawah,
        "batas_atas_h7_rp": batas_atas,
        "perubahan_persen": perubahan_persen,
        "metode": "ann_perceptron_5_16_1",
        "horizon_hari": 7,
        "input_lags": {
            "h_t": int(x_lags[0]),
            "h_t_1": int(x_lags[1]),
            "h_t_7": int(x_lags[2]),
            "h_t_14": int(x_lags[3]),
            "h_t_21": int(x_lags[4]),
        },
        "metrik_model": model_info.get("metrik_uji"),
    }


def ringkasan_evaluasi() -> dict[str, Any]:
    """Kembalikan metadata dan ringkasan metrik evaluasi 162 model ANN Perceptron."""
    paket = _muat_bobot()
    if not paket.get("models"):
        return {"tersedia": False, "catatan": "Model ANN Perceptron belum dilatih"}
    return {
        "tersedia": True,
        "meta": paket.get("meta", {}),
        "ringkasan_evaluasi_per_komoditas": paket.get("ringkasan_evaluasi_per_komoditas", {}),
    }
