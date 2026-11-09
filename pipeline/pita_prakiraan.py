"""Hitung pita prakiraan 7 hari dari sebaran empiris (bukan asumsi normal).

Keluaran: data/derived/pita_prakiraan.json
Isi per (sumber, komoditas): q10, q50, q90 dari perubahan 7 hari, plus statistik uji.

Dasar: walk-forward menunjukkan naive (harga terakhir) paling akurat;
pita berbasis sigma hanya mencakup 69-75%, sedangkan kuantil empiris 85%.
"""

from __future__ import annotations

import csv
import glob
import json
import pathlib
import statistics as st

RAW = pathlib.Path(__file__).resolve().parents[1] / "data" / "raw"
OUT = pathlib.Path(__file__).resolve().parents[1] / "data" / "derived" / "pita_prakiraan.json"
H = 7
MIN_OBS = 60
BAGI_LATIH = 0.7


def muat() -> dict[tuple[str, str, str], list[int]]:
    seri: dict[tuple[str, str, str], dict[str, int]] = {}
    paket = RAW.parent / "paket" / "bapanas.csv.gz"
    if paket.exists():
        import gzip
        with gzip.open(paket, "rt", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                if (r.get("tingkat") or "konsumen") != "konsumen":
                    continue
                if not (r.get("harga_rp") or "").isdigit():
                    continue
                kunci = ("bapanas", r["wilayah"], r["komoditas"])
                seri.setdefault(kunci, {})[r["tanggal"]] = int(r["harga_rp"])
        return {k: [v for _, v in sorted(d.items())] for k, d in seri.items() if len(d) >= MIN_OBS}
    return {k: [v for _, v in sorted(d.items())] for k, d in seri.items() if len(d) >= MIN_OBS}


def kuantil(data: list[float], p: float) -> float:
    urut = sorted(data)
    if not urut:
        return 0.0
    return urut[min(len(urut) - 1, max(0, int(p * (len(urut) - 1))))]


def main() -> int:
    data = muat()
    latih: dict[tuple[str, str], list[float]] = {}
    uji: dict[tuple[str, str], list[float]] = {}
    for (sumber, _w, kom), x in data.items():
        r7 = [(x[i + H] - x[i]) / x[i] for i in range(len(x) - H) if x[i] > 0]
        potong = int(len(r7) * BAGI_LATIH)
        latih.setdefault((sumber, kom), []).extend(r7[:potong])
        uji.setdefault((sumber, kom), []).extend(r7[potong:])

    hasil: dict[str, dict] = {}
    cakupan_total: list[float] = []
    for (sumber, kom), nilai in sorted(latih.items()):
        if len(nilai) < 50:
            continue
        q10, q50, q90 = kuantil(nilai, .10), kuantil(nilai, .50), kuantil(nilai, .90)
        u = uji.get((sumber, kom), [])
        cakup = (
            round(sum(1 for r in u if q10 <= r <= q90) / len(u) * 100, 1) if u else None
        )
        if cakup is not None:
            cakupan_total.append(cakup)
        hasil[f"{sumber}|{kom}"] = {
            "q10": round(q10, 4),
            "q50": round(q50, 4),
            "q90": round(q90, 4),
            "cakupan_uji_pct": cakup,
            "n_latih": len(nilai),
            "n_uji": len(u),
        }

    payload = {
        "horizon_hari": H,
        "metode_titik": "naive (harga terakhir)",
        "metode_pita": "kuantil empiris perubahan 7 hari",
        "cakupan_rata_rata_pct": round(st.mean(cakupan_total), 1) if cakupan_total else None,
        "per_sumber_komoditas": hasil,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"ok: {len(hasil)} kombinasi -> {OUT.name} | cakupan rata-rata {payload['cakupan_rata_rata_pct']}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
