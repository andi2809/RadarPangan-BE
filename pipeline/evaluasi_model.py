"""Evaluasi walk-forward sesuai DATA_PIPELINE §4.3 (format `evaluasi_model`).

4 fold expanding window, horizon h=1..7, metrik MAPE, sMAPE, MASE, Coverage80,
Pinball (α=0,10/0,50/0,90), plus gerbang promosi model per komoditas.

Keluaran: data/derived/evaluasi_model_bapanas_<tanggal>.json
"""

from __future__ import annotations

import csv
import datetime as dt
import gzip
import json
import pathlib
import statistics as st
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parents[1]
PAKET = ROOT / "data" / "paket" / "bapanas.csv.gz"
PITA = ROOT / "data" / "derived" / "pita_prakiraan.json"
DERIVED = ROOT / "data" / "derived"

H = 7
FOLD = 4
MIN_OBS = 400
ALPHA = (0.10, 0.50, 0.90)


def muat() -> dict[tuple[str, str], list[int]]:
    seri: dict[tuple[str, str], dict[str, int]] = defaultdict(dict)
    with gzip.open(PAKET, "rt", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if (r.get("tingkat") or "konsumen") != "konsumen":
                continue
            if not (r.get("harga_rp") or "").isdigit():
                continue
            seri[(r["wilayah"], r["komoditas"])][r["tanggal"]] = int(r["harga_rp"])
    return {k: [v for _, v in sorted(d.items())] for k, d in seri.items() if len(d) >= MIN_OBS}


def muat_pita() -> dict[str, tuple[float, float]]:
    if not PITA.exists():
        return {}
    data = json.loads(PITA.read_text(encoding="utf-8")).get("per_sumber_komoditas", {})
    return {k.split("|")[1]: (v["q10"], v["q90"]) for k, v in data.items()}


def ses(x, a=0.35):
    lvl = float(x[0])
    for v in x[1:]:
        lvl = a * v + (1 - a) * lvl
    return lvl


def holt(x, a=0.3, b=0.1, h=1):
    lvl, tr = float(x[0]), x[1] - x[0]
    for v in x[1:]:
        l0, lvl = lvl, a * v + (1 - a) * (lvl + tr)
        tr = b * (lvl - l0) + (1 - b) * tr
    return lvl + h * tr


def hw(x, a=0.3, b=0.1, g=0.1, p=7, h=1):
    if len(x) < 2 * p:
        return x[-1]
    lvl = st.mean(x[:p]); tr = (st.mean(x[p:2 * p]) - st.mean(x[:p])) / p
    musim = [v - lvl for v in x[:p]]
    for i, v in enumerate(x[p:], start=p):
        s = musim[i % p]; l0 = lvl
        lvl = a * (v - s) + (1 - a) * (lvl + tr)
        tr = b * (lvl - l0) + (1 - b) * tr
        musim[i % p] = g * (v - lvl) + (1 - g) * s
    return lvl + h * tr + musim[(len(x) + h) % p]


MODEL = {
    "naive": lambda x, h: x[-1],
    "seasonal_naive7": lambda x, h: x[-7] if len(x) >= 7 else x[-1],
    "ma7": lambda x, h: st.mean(x[-7:]) if len(x) >= 7 else x[-1],
    "ses": lambda x, h: ses(x),
    "holt": lambda x, h: holt(x, h=h),
    "holt_winters": lambda x, h: hw(x, h=h),
}
BASELINE = ("naive", "seasonal_naive7", "ma7")


def pinball(y, q, alpha):
    return max(alpha * (y - q), (alpha - 1) * (y - q))


def main() -> int:
    data = muat()
    pita = muat_pita()
    metrik: dict[tuple[str, str], dict] = defaultdict(lambda: defaultdict(list))

    for (_w, komoditas), v in data.items():
        n = len(v)
        for k in range(1, FOLD + 1):
            titik = n - H * (FOLD - k + 1)
            if titik < MIN_OBS:
                continue
            hist = v[:titik]
            mae_naive = st.mean(abs(hist[i] - hist[i - 1]) for i in range(1, len(hist))) or 1
            q10, q90 = pita.get(komoditas, (0.0, 0.0))
            for h in range(1, H + 1):
                if titik + h - 1 >= n:
                    break
                aktual = v[titik + h - 1]
                for nama, fn in MODEL.items():
                    pred = fn(hist, h)
                    metrik[(komoditas, nama)]["mape"].append(abs(pred - aktual) / aktual * 100)
                    metrik[(komoditas, nama)]["smape"].append(
                        200 * abs(pred - aktual) / (abs(pred) + abs(aktual))
                    )
                    metrik[(komoditas, nama)]["mase"].append(abs(pred - aktual) / mae_naive)
                # interval memakai kuantil empiris komoditas (median = baseline naive)
                lo, med, hi = v[titik - 1] * (1 + q10), v[titik - 1], v[titik - 1] * (1 + q90)
                metrik[(komoditas, "pita_empiris")]["coverage80"].append(lo <= aktual <= hi)
                metrik[(komoditas, "pita_empiris")]["pinball"].append(
                    (pinball(aktual, lo, 0.10) + pinball(aktual, med, 0.50) + pinball(aktual, hi, 0.90)) / 3
                )

    hasil: dict[str, dict] = {}
    for komoditas in sorted({k for k, _ in metrik}):
        baris: dict[str, dict] = {}
        for nama in list(MODEL) + ["pita_empiris"]:
            m = metrik.get((komoditas, nama), {})
            if not m.get("mape"):
                continue
            baris[nama] = {
                "n": len(m["mape"]),
                "mape": round(st.mean(m["mape"]), 3),
                "smape": round(st.mean(m["smape"]), 3),
                "mase": round(st.mean(m["mase"]), 3),
                "coverage80": round(st.mean(m.get("coverage80", [0])), 3) if m.get("coverage80") else None,
                "pinball": round(st.mean(m["pinball"]), 2) if m.get("pinball") else None,
            }
        baseline_terbaik = min(
            (n for n in BASELINE if n in baris), key=lambda n: baris[n]["smape"], default=None
        )
        kandidat = [n for n in ("ses", "holt", "holt_winters") if n in baris]
        pemenang = baseline_terbaik
        alasan = "baseline terbaik (tidak ada kandidat kompleks yang lolos gerbang)"
        if baseline_terbaik and kandidat:
            k = min(kandidat, key=lambda n: baris[n]["smape"])
            smape_baseline = baris[baseline_terbaik]["smape"]
            lolos_1 = baris[k]["smape"] <= smape_baseline * 0.98
            lolos_2 = baris[k]["mase"] < 1.0
            cov = baris["pita_empiris"]["coverage80"] if "pita_empiris" in baris else None
            lolos_3 = cov is not None and 0.72 <= cov <= 0.92
            if lolos_1 and lolos_2 and lolos_3:
                pemenang, alasan = k, "kandidat lolos gerbang promosi"
        hasil[komoditas] = {"model": baris, "aktif": pemenang, "alasan": alasan}

    tanggal = dt.date.today().isoformat()
    OUT = DERIVED / f"evaluasi_model_bapanas_{tanggal}.json"
    payload = {
        "tanggal_data": tanggal,
        "spesifikasi": "DATA_PIPELINE §4.3 (4 fold expanding, h=1..7)",
        "metrik": ["mape", "smape", "mase", "coverage80", "pinball"],
        "gerbang_promosi": "sMAPE <= 98% baseline DAN MASE<1,00 DAN Coverage80 0,72-0,92",
        "n_seri": len(data),
        "komoditas": hasil,
    }
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"ok -> {OUT.name} | {len(data)} seri | {len(hasil)} komoditas")
    for kom, v in hasil.items():
        print(f"  {kom:22s} aktif={v['aktif']:14s} {v['alasan'][:44]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
