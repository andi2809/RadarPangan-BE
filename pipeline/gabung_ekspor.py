"""Gabungkan snapshot PIHPS + SP2KP menjadi satu CSV siap pakai (dengan label sumber).

Keluaran: data/derived/gabungan_harga.csv
Kolom: tanggal, wilayah, komoditas, harga_rp, sumber, jenis_harga

Aturan:
- PIHPS selalu `jenis_harga=pasar`.
- SP2KP `pasar` hanya untuk cabai & bawang (seri yang benar-benar bergerak);
  selain itu `acuan` (lihat PROTOKOL §7–§9).
- Baris ganda untuk kunci yang sama diambil dari berkas terakhir (snapshot terbaru).
"""

from __future__ import annotations

import csv
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import runlog  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "derived" / "gabungan_harga.csv"

SP2KP_PASAR = {"cabai_rawit_merah", "bawang_merah"}


def baca(pola: str, sumber: str) -> list[dict]:
    hasil = []
    for path in sorted(RAW.glob(pola)):
        with path.open(encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                nilai = (row.get("harga_rp") or "").strip()
                if not nilai.isdigit():
                    continue
                komoditas = row["komoditas"]
                jenis = "pasar"
                if sumber == "sp2kp" and komoditas not in SP2KP_PASAR:
                    jenis = "acuan"
                hasil.append(
                    {
                        "tanggal": row["tanggal"],
                        "wilayah": row["wilayah"],
                        "komoditas": komoditas,
                        "harga_rp": int(nilai),
                        "sumber": sumber,
                        "jenis_harga": jenis,
                    }
                )
    return hasil


def main() -> int:
    ctx = runlog.mulai("gabungan")
    baris = baca("pihps_jabar_*.csv", "pihps") + baca("sp2kp_jabar_*.csv", "sp2kp")
    if not baris:
        runlog.selesai(ctx, status="kosong", pesan="tidak ada snapshot")
        print("tidak ada snapshot")
        return 1

    terakhir: dict[tuple, dict] = {}
    for r in baris:
        terakhir[(r["tanggal"], r["wilayah"], r["komoditas"], r["sumber"])] = r
    hasil = sorted(terakhir.values(), key=lambda d: (d["tanggal"], d["wilayah"], d["komoditas"], d["sumber"]))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["tanggal", "wilayah", "komoditas", "harga_rp", "sumber", "jenis_harga"])
        w.writeheader()
        w.writerows(hasil)

    per_sumber = {s: sum(1 for r in hasil if r["sumber"] == s) for s in ("pihps", "sp2kp")}
    print(f"ok: {len(hasil)} baris -> {OUT.name} ({OUT.stat().st_size // 1024} KB)")
    print(f"  sumber  : {per_sumber}")
    print(f"  wilayah : {len({r['wilayah'] for r in hasil})}")
    print(f"  periode : {hasil[0]['tanggal']} s/d {hasil[-1]['tanggal']}")
    runlog.selesai(ctx, status="ok", berkas=OUT, jumlah_baris=len(hasil))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
