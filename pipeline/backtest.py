"""Backtest EWS: apakah status "kritis" benar-benar mendahului lonjakan harga?

Definisi (dibuat eksplisit supaya bisa dibantah):
- ALARM pada hari t = status hasil ambang selisih terhadap acuan (HET/HAP) melewati batas.
- KEJADIAN pada hari t = harga naik >= AMBANG_NAIK dalam HORIZON hari ke depan.
- Lead time = jarak hari dari alarm pertama ke puncak kenaikan.

Keluaran: data/derived/backtest_<tanggal>.json + tabel ringkas di stdout.
"""

from __future__ import annotations

import argparse
import csv
import json
import pathlib
import statistics
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import runlog  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services import harga as harga_service  # noqa: E402

HORIZON = 7          # hari ke depan
AMBANG_NAIK = 3.0    # % kenaikan yang dianggap "kejadian"
AKUAN = {            # sama dengan app/routers/peta.py ACUAN
    "beras_medium": (13500, "HET"),
    "cabai_rawit_merah": (45000, "HAP"),
    "bawang_merah": (32000, "HAP"),
    "telur_ayam_ras": (29500, "DINAMIS"),
    "minyak_goreng_curah": (15700, "HET"),
}
AMBANG_STATUS = {"waspada": 5.0, "kritis": 10.0}


def _wilayah() -> list[str]:
    path = ROOT / "data" / "referensi" / "umk_jabar_2026.csv"
    with path.open(encoding="utf-8") as fh:
        return [r["nama_wilayah"] for r in csv.DictReader(fh)]


def _acuan_dinamis(seri: list[tuple[str, int]], i: int, jendela: int = 90) -> float | None:
    nilai = [h for _t, h in seri[max(0, i - jendela):i]]
    return statistics.median(nilai) if nilai else None


def evaluasi(komoditas: str, ambang: float) -> dict:
    acuan_tetap, jenis = AKUAN[komoditas]
    tp = fp = fn = tn = 0
    lead: list[int] = []
    contoh: list[dict] = []

    for wilayah in _wilayah():
        seri = harga_service.seri(wilayah, komoditas)
        if len(seri) <= HORIZON:
            continue
        for i, (tanggal, harga) in enumerate(seri[:-HORIZON]):
            dasar = acuan_tetap
            if jenis == "DINAMIS":
                dasar = _acuan_dinamis(seri, i) or acuan_tetap
            selisih = (harga - dasar) / dasar * 100
            alarm = selisih > ambang

            depan = seri[i + 1:i + 1 + HORIZON]
            naik = max((h - harga) / harga * 100 for _t, h in depan) if depan else 0.0
            kejadian = naik >= AMBANG_NAIK

            if alarm and kejadian:
                tp += 1
                puncak = max(range(len(depan)), key=lambda k: depan[k][1]) + 1
                lead.append(puncak)
                if len(contoh) < 3:
                    contoh.append({"wilayah": wilayah, "tanggal": tanggal, "selisih": round(selisih, 1), "naik_h7": round(naik, 1)})
            elif alarm and not kejadian:
                fp += 1
            elif not alarm and kejadian:
                fn += 1
            else:
                tn += 1

    presisi = round(tp / (tp + fp) * 100, 1) if (tp + fp) else None
    recall = round(tp / (tp + fn) * 100, 1) if (tp + fn) else None
    return {
        "komoditas": komoditas,
        "ambang_persen": ambang,
        "n_observasi": tp + fp + fn + tn,
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "precision_pct": presisi,
        "recall_pct": recall,
        "lead_time_median_hari": round(statistics.median(lead), 1) if lead else None,
        "contoh_alarm_benar": contoh,
    }


def evaluasi_momentum(komoditas: str, ambang_pct: float) -> dict:
    """Sinyal alternatif: harga naik >= ambang_pct dibanding median 30 hari sebelumnya."""
    tp = fp = fn = tn = 0
    lead: list[int] = []
    for wilayah in _wilayah():
        seri = harga_service.seri(wilayah, komoditas)
        if len(seri) <= 30 + HORIZON:
            continue
        for i in range(30, len(seri) - HORIZON):
            tanggal, harga = seri[i]
            dasar = statistics.median(h for _t, h in seri[i - 30:i])
            alarm = dasar > 0 and (harga - dasar) / dasar * 100 >= ambang_pct
            depan = seri[i + 1:i + 1 + HORIZON]
            naik = max((h - harga) / harga * 100 for _t, h in depan) if depan else 0.0
            kejadian = naik >= AMBANG_NAIK
            if alarm and kejadian:
                tp += 1
                lead.append(max(range(len(depan)), key=lambda k: depan[k][1]) + 1)
            elif alarm:
                fp += 1
            elif kejadian:
                fn += 1
            else:
                tn += 1
    presisi = round(tp / (tp + fp) * 100, 1) if (tp + fp) else None
    recall = round(tp / (tp + fn) * 100, 1) if (tp + fn) else None
    return {"komoditas": komoditas, "ambang_persen": ambang_pct, "n": tp + fp + fn + tn,
            "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "precision_pct": presisi, "recall_pct": recall,
            "lead_time_median_hari": round(statistics.median(lead), 1) if lead else None}


def main() -> int:
    ap = argparse.ArgumentParser(description="Backtest EWS harga pangan")
    ap.add_argument("--ambang", type=float, default=AMBANG_STATUS["kritis"])
    args = ap.parse_args()

    cak = harga_service.cakupan()
    tanggal = cak["periode"][1] if cak["periode"] else "-"
    ctx = runlog.mulai("backtest_ews")

    hasil = [evaluasi(k, args.ambang) for k in AKUAN]
    print(f"Backtest EWS — horizon {HORIZON} hari, kejadian = naik >= {AMBANG_NAIK}%, ambang status > {args.ambang}%\n")
    print(f"{'komoditas':20s} {'n':>5s} {'TP':>4s} {'FP':>4s} {'FN':>4s} {'presisi':>8s} {'recall':>7s} {'lead':>5s}")
    for r in hasil:
        print(f"{r['komoditas']:20s} {r['n_observasi']:5d} {r['tp']:4d} {r['fp']:4d} {r['fn']:4d} "
              f"{(str(r['precision_pct'])+'%'):>8s} {(str(r['recall_pct'])+'%'):>7s} {str(r['lead_time_median_hari']):>5s}")

    momentum = {amb: [evaluasi_momentum(k, amb) for k in AKUAN] for amb in (1.0, 2.0, 3.0)}
    print("\nSinyal momentum (harga vs median 30 hari):")
    for amb, baris in momentum.items():
        rata_p = [r["precision_pct"] for r in baris if r["precision_pct"] is not None]
        rata_r = [r["recall_pct"] for r in baris if r["recall_pct"] is not None]
        f1 = [2 * (r["precision_pct"] * r["recall_pct"]) / (r["precision_pct"] + r["recall_pct"])
              for r in baris if r["precision_pct"] and r["recall_pct"]]
        print(f"  ambang {amb:>3}%: presisi rata2 {round(statistics.mean(rata_p),1) if rata_p else '-'}%  "
              f"recall rata2 {round(statistics.mean(rata_r),1) if rata_r else '-'}%  "
              f"F1 {round(statistics.mean(f1),1) if f1 else '-'}")

    tujuan = ROOT / "data" / "derived" / f"backtest_{tanggal}.json"
    tujuan.parent.mkdir(parents=True, exist_ok=True)
    tujuan.write_text(json.dumps({
        "tanggal_data": tanggal,
        "definisi": {
            "horizon_hari": HORIZON,
            "kejadian": f"harga naik >= {AMBANG_NAIK}% dalam {HORIZON} hari",
            "alarm": f"selisih terhadap acuan (HET/HAP) > {args.ambang}%",
            "catatan": "hasil ini mengukur kinerja ambang, bukan kualitas produk; sampel kecil (9 wilayah, 60 hari)",
        },
        "komoditas": hasil,
        "sinyal_momentum": momentum,
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n-> {tujuan}")
    runlog.selesai(ctx, status="ok", berkas=tujuan, jumlah_baris=len(hasil))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
