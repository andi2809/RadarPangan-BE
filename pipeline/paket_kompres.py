"""Bentuk paket terkompresi untuk bundel serverless (satu berkas per sumber).

Masukan : data/raw/*.csv (arsip penuh)
Keluaran: data/paket/pihps.csv.gz, data/paket/sp2kp.csv.gz

Alasan: bundel Vercel ikut membawa data. CSV mentah 7 MB menjadi ±1,3 MB setelah
dikompresi dan digabung, sehingga cold start dan unduhan build lebih ringan.
Arsip mentah tetap disimpan di git untuk audit.
"""

from __future__ import annotations

import csv
import glob
import gzip
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "paket"

KOLOM = {
    "pihps": ["tanggal", "regency_id_pihps", "wilayah", "komoditas", "harga_rp", "sumber"],
    "sp2kp": ["tanggal", "wilayah", "komoditas", "harga_rp", "sumber"],
}


def gabung(sumber: str) -> tuple[list[dict], int]:
    baris: dict[tuple[str, str, str], dict] = {}
    duplikat = 0
    for f in sorted(glob.glob(str(RAW / f"{sumber}_jabar_*.csv"))):
        with open(f, encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                kunci = (r["tanggal"], r["wilayah"], r["komoditas"])
                if kunci in baris:
                    duplikat += 1
                baris[kunci] = r
    return [baris[k] for k in sorted(baris)], duplikat


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for sumber in ("pihps", "sp2kp"):
        data, duplikat = gabung(sumber)
        tujuan = OUT / f"{sumber}.csv.gz"
        with gzip.open(tujuan, "wt", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=KOLOM[sumber], extrasaction="ignore")
            w.writeheader()
            w.writerows(data)
        asli = sum(pathlib.Path(f).stat().st_size for f in glob.glob(str(RAW / f"{sumber}_jabar_*.csv")))
        print(
            f"{sumber:6s}: {len(data):6d} baris (duplikat dibuang {duplikat}) "
            f"| {asli / 1e6:.1f} MB -> {tujuan.stat().st_size / 1e6:.2f} MB"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
