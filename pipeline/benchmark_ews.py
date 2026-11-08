#!/usr/bin/env python3
"""Benchmark model prakiraan harga H+7 pada dataset Bapanas (rolling-origin).

Target: harga H+7 per kab/kota/komoditas. Satu langkah = 7 observasi
(hari pelaporan), bukan 7 hari kalender — sama dengan pipeline/pita_prakiraan.py.

Model yang dibandingkan (parameter tetap, tanpa tuning per seri):
- naive                 : harga terakhir
- seasonal_naive        : nilai 7 observasi lalu; pada H=7 identik dengan naive
- ses                   : simple exponential smoothing, alpha=0.35
- holt                  : level + trend, alpha=0.30, beta=0.10
- holt_winters          : level + trend + musiman mingguan, alpha=0.30, beta=0.10, gamma=0.10
- drift3                : slope 3 observasi terakhir (pembanding implementasi lama)

Validasi: 30% observasi terakhir tiap seri dipakai sebagai test; origin digeser
`--step` observasi (default 1 = semua origin; 7 = non-overlap). Metrik: MAPE
median/mean, MASE dengan skala naive in-sample, dan cakupan pita empiris dari
data/derived/pita_prakiraan.json. Hasil ditulis ke
data/derived/benchmark_ews_bapanas_<tanggal-data>.json.

Catatan: pita empiris dikalibrasi untuk prakiraan naive; cakupan model lain
dilaporkan sebagai pembanding, bukan klaim interval terkalibrasi.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import pathlib
import statistics

ROOT = pathlib.Path(__file__).resolve().parents[1]
PAKET = ROOT / "data" / "paket" / "bapanas.csv.gz"
PITA = ROOT / "data" / "derived" / "pita_prakiraan.json"
OUT_DIR = ROOT / "data" / "derived"

HORIZON = 7
PERIODE = 7
MIN_TRAIN = 60
TRAIN_FRAC = 0.7

PARAM = {
    "ses": {"alpha": 0.35},
    "holt": {"alpha": 0.30, "beta": 0.10},
    "holt_winters": {"alpha": 0.30, "beta": 0.10, "gamma": 0.10},
}

MODELS = ["naive", "seasonal_naive", "ses", "holt", "holt_winters", "drift3"]


def muat_seri() -> tuple[dict[tuple[str, str], list[int]], str]:
    """Bapanas konsumen -> ({(wilayah, komoditas): [harga per tanggal]}, tanggal maksimum)."""
    data: dict[tuple[str, str], dict[str, int]] = {}
    tanggal: list[str] = []
    with gzip.open(PAKET, "rt", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if (row.get("tingkat") or "konsumen") != "konsumen":
                continue
            nilai = (row.get("harga_rp") or "").strip()
            if not nilai.isdigit():
                continue
            kunci = (row["wilayah"], row["komoditas"])
            data.setdefault(kunci, {})[row["tanggal"]] = int(nilai)
            tanggal.append(row["tanggal"])
    return (
        {k: [v for _, v in sorted(d.items())] for k, d in data.items()},
        max(tanggal) if tanggal else "-",
    )


def muat_pita() -> dict[str, dict]:
    try:
        return json.loads(PITA.read_text(encoding="utf-8")).get("per_sumber_komoditas", {})
    except (OSError, ValueError):
        return {}


def state_ses(nilai: list[int], alpha: float) -> list[float]:
    level = [0.0] * len(nilai)
    level[0] = nilai[0]
    for i in range(1, len(nilai)):
        level[i] = alpha * nilai[i] + (1 - alpha) * level[i - 1]
    return level


def state_holt(nilai: list[int], alpha: float, beta: float) -> tuple[list[float], list[float]]:
    n = len(nilai)
    level = [0.0] * n
    trend = [0.0] * n
    level[0] = nilai[0]
    trend[0] = (nilai[1] - nilai[0]) if n > 1 else 0.0
    for i in range(1, n):
        l_prev, t_prev = level[i - 1], trend[i - 1]
        level[i] = alpha * nilai[i] + (1 - alpha) * (l_prev + t_prev)
        trend[i] = beta * (level[i] - l_prev) + (1 - beta) * t_prev
    return level, trend


def state_hw(
    nilai: list[int], alpha: float, beta: float, gamma: float
) -> tuple[list[float], list[float], list[list[float]]]:
    n = len(nilai)
    level = [0.0] * n
    trend = [0.0] * n
    musiman = [[0.0] * PERIODE for _ in range(n)]
    if n < 2 * PERIODE:
        lv, tr = state_holt(nilai, alpha, beta)
        return lv, tr, musiman

    lv = sum(nilai[:PERIODE]) / PERIODE
    tr = (sum(nilai[PERIODE:2 * PERIODE]) / PERIODE - lv) / PERIODE
    s = [nilai[j] - lv for j in range(PERIODE)]
    level[PERIODE - 1], trend[PERIODE - 1], musiman[PERIODE - 1] = lv, tr, s[:]
    for i in range(PERIODE, n):
        s_lama = s[i % PERIODE]
        lv_baru = alpha * (nilai[i] - s_lama) + (1 - alpha) * (lv + tr)
        tr_baru = beta * (lv_baru - lv) + (1 - beta) * tr
        s[i % PERIODE] = gamma * (nilai[i] - lv_baru) + (1 - gamma) * s_lama
        lv, tr = lv_baru, tr_baru
        level[i], trend[i], musiman[i] = lv, tr, s[:]
    return level, trend, musiman


def prakiraan(model: str, nilai: list[int], i: int, state: dict) -> float:
    if model == "naive":
        return float(nilai[i])
    if model == "seasonal_naive":
        j = i + HORIZON - PERIODE
        return float(nilai[j] if j >= 0 else nilai[i])
    if model == "ses":
        return state["ses"][i]
    if model == "holt":
        level, trend = state["holt"]
        return level[i] + HORIZON * trend[i]
    if model == "holt_winters":
        level, trend, musiman = state["hw"]
        return level[i] + HORIZON * trend[i] + musiman[i][i % PERIODE]
    if model == "drift3":
        if i < 3:
            return float(nilai[i])
        return nilai[i] + HORIZON * (nilai[i] - nilai[i - 3]) / 3
    raise ValueError(model)


def ringkas(ape: list[float], mase: list[float], cakupan: list[bool]) -> dict:
    if not ape:
        return {"n": 0, "mape_median": None, "mape_mean": None,
                "mase_median": None, "cakupan_pct": None}
    return {
        "n": len(ape),
        "mape_median": round(statistics.median(ape), 2),
        "mape_mean": round(statistics.mean(ape), 2),
        "mase_median": round(statistics.median(mase), 3) if mase else None,
        "cakupan_pct": round(sum(cakupan) / len(cakupan) * 100, 1) if cakupan else None,
    }


def evaluasi(
    seri: dict[tuple[str, str], list[int]],
    pita: dict[str, dict],
    step: int,
    train_frac: float,
    min_train: int,
) -> dict:
    ape: dict[str, dict[str, list[float]]] = {m: {} for m in MODELS}
    mase: dict[str, dict[str, list[float]]] = {m: {} for m in MODELS}
    cakupan: dict[str, dict[str, list[bool]]] = {m: {} for m in MODELS}
    menang: dict[str, int] = {m: 0 for m in MODELS}
    jumlah_seri = 0
    total_forecast = 0

    for (wilayah, komoditas), nilai in sorted(seri.items()):
        n = len(nilai)
        if n < min_train + HORIZON:
            continue
        jumlah_seri += 1
        mulai = max(min_train, int((n - HORIZON) * train_frac))
        if mulai >= n - HORIZON:
            continue

        kumulatif = [0.0] * n
        for i in range(1, n):
            kumulatif[i] = kumulatif[i - 1] + abs(nilai[i] - nilai[i - 1])
        skala = kumulatif[mulai] / mulai if mulai > 0 else 0.0

        state = {
            "ses": state_ses(nilai, PARAM["ses"]["alpha"]),
            "holt": state_holt(nilai, PARAM["holt"]["alpha"], PARAM["holt"]["beta"]),
            "hw": state_hw(
                nilai,
                PARAM["holt_winters"]["alpha"],
                PARAM["holt_winters"]["beta"],
                PARAM["holt_winters"]["gamma"],
            ),
        }
        pita_kom = pita.get(f"bapanas|{komoditas}") or {}
        q10, q90 = pita_kom.get("q10"), pita_kom.get("q90")

        ape_seri: dict[str, list[float]] = {m: [] for m in MODELS}
        for i in range(mulai, n - HORIZON, step):
            aktual = nilai[i + HORIZON]
            if aktual <= 0:
                continue
            total_forecast += 1
            for m in MODELS:
                pred = prakiraan(m, nilai, i, state)
                galat = abs(pred - aktual)
                nilai_ape = galat / aktual * 100
                ape[m].setdefault(komoditas, []).append(nilai_ape)
                ape_seri[m].append(nilai_ape)
                if skala > 0:
                    mase[m].setdefault(komoditas, []).append(galat / skala)
                if q10 is not None and q90 is not None:
                    cakupan[m].setdefault(komoditas, []).append(
                        pred * (1 + q10) <= aktual <= pred * (1 + q90)
                    )

        median_seri = {
            m: statistics.median(v) for m, v in ape_seri.items() if v
        }
        if median_seri:
            terbaik = min(median_seri.values())
            for m, v in median_seri.items():
                if abs(v - terbaik) < 1e-12:
                    menang[m] += 1

    per_komoditas: dict[str, dict] = {}
    for m in MODELS:
        for kom in ape[m]:
            per_komoditas.setdefault(kom, {})[m] = ringkas(
                ape[m][kom], mase[m].get(kom, []), cakupan[m].get(kom, [])
            )

    overall = {}
    for m in MODELS:
        semua_ape = [x for v in ape[m].values() for x in v]
        semua_mase = [x for v in mase[m].values() for x in v]
        semua_cakupan = [x for v in cakupan[m].values() for x in v]
        overall[m] = ringkas(semua_ape, semua_mase, semua_cakupan)

    return {
        "n_seri": jumlah_seri,
        "n_forecast": total_forecast,
        "per_komoditas": per_komoditas,
        "overall": overall,
        "menang_seri": menang,
    }


def cetak(hasil: dict, step: int) -> None:
    print(f"Benchmark EWS H+{HORIZON} — Bapanas, {hasil['n_seri']} seri, "
          f"{hasil['n_forecast']} forecast, step {step}")
    print(f"{'komoditas':22s} {'model':16s} {'n':>7s} {'MAPE med':>9s} "
          f"{'MAPE mean':>10s} {'MASE med':>9s} {'cakupan':>8s}")
    for kom, baris in sorted(hasil["per_komoditas"].items()):
        urut = sorted(baris.items(), key=lambda kv: (kv[1]["mape_median"] is None,
                                                     kv[1]["mape_median"]))
        for model, r in urut:
            print(f"{kom:22s} {model:16s} {r['n']:7d} "
                  f"{str(r['mape_median']):>9s} {str(r['mape_mean']):>10s} "
                  f"{str(r['mase_median']):>9s} {str(r['cakupan_pct']):>8s}")
        print()

    print("Overall (semua komoditas):")
    urut = sorted(hasil["overall"].items(), key=lambda kv: (kv[1]["mape_median"] is None,
                                                           kv[1]["mape_median"]))
    for model, r in urut:
        print(f"  {model:16s} n={r['n']:6d}  MAPE med {r['mape_median']}%  "
              f"mean {r['mape_mean']}%  MASE {r['mase_median']}  "
              f"cakupan {r['cakupan_pct']}%")
    print("\nSeri terbaik (termasuk seri bila imbang):",
          {m: hasil["menang_seri"][m] for m in MODELS})


def main() -> int:
    ap = argparse.ArgumentParser(description="Benchmark prakiraan harga H+7 (Bapanas)")
    ap.add_argument("--step", type=int, default=1, help="geser origin (1=semua, 7=non-overlap)")
    ap.add_argument("--train-frac", type=float, default=TRAIN_FRAC)
    ap.add_argument("--min-train", type=int, default=MIN_TRAIN)
    args = ap.parse_args()

    seri, tanggal_data = muat_seri()
    pita = muat_pita()
    hasil = evaluasi(seri, pita, args.step, args.train_frac, args.min_train)
    hasil.update({
        "tanggal_data": tanggal_data,
        "horizon": HORIZON,
        "periode_seasonal": PERIODE,
        "split": f"{args.train_frac:.0%} observasi terakhir per seri",
        "step": args.step,
        "parameter_model": PARAM,
        "catatan": [
            "H+7 = 7 observasi/hari pelaporan, bukan 7 hari kalender.",
            "seasonal_naive pada H=7 identik dengan naive; hanya berbeda untuk H<7.",
            "Pita empiris dikalibrasi untuk naive; cakupan model lain hanya pembanding.",
            "MASE memakai skala naive in-sample; seri datar (skala 0) tidak dihitung.",
        ],
    })
    cetak(hasil, args.step)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tujuan = OUT_DIR / f"benchmark_ews_bapanas_{tanggal_data}_step{args.step}.json"
    tujuan.write_text(json.dumps(hasil, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\n-> {tujuan}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
