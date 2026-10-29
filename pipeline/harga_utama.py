"""Bentuk satu tabel "harga utama" untuk FE: prioritas PIHPS, tambalan SP2KP.

Aturan (tanpa merata-ratakan apa pun):
1. Untuk (tanggal, wilayah, komoditas) yang punya data PIHPS -> pakai PIHPS (`pasar`).
2. Bila tidak ada -> pakai SP2KP (`pasar` untuk cabai/bawang, `acuan` untuk lainnya).
3. Tidak ada data -> baris tidak dibuat (jangan diisi nol/tebakan).

Keluaran: data/derived/harga_utama.csv
Kolom: tanggal, kode_kemendagri, wilayah, komoditas, harga_rp, sumber, jenis_harga
"""

from __future__ import annotations

import csv
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import runlog  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
REF = ROOT / "data" / "referensi" / "umk_jabar_2026.csv"
OUT = ROOT / "data" / "derived" / "harga_utama.csv"

SP2KP_PASAR = {"cabai_rawit_merah", "bawang_merah"}


def kode_wilayah() -> dict[str, str]:
    with REF.open(encoding="utf-8") as fh:
        return {r["nama_wilayah"]: r["kode_kemendagri"] for r in csv.DictReader(fh)}


def baca(pola: str, sumber: str) -> dict[tuple[str, str, str], dict]:
    hasil: dict[tuple[str, str, str], dict] = {}
    for path in sorted(RAW.glob(pola)):
        with path.open(encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                nilai = (row.get("harga_rp") or "").strip()
                if not nilai.isdigit():
                    continue
                kunci = (row["tanggal"], row["wilayah"], row["komoditas"])
                jenis = "pasar"
                if sumber == "sp2kp" and row["komoditas"] not in SP2KP_PASAR:
                    jenis = "acuan"
                hasil[kunci] = {**row, "harga_rp": int(nilai), "sumber": sumber, "jenis_harga": jenis}
    return hasil


def main() -> int:
    ctx = runlog.mulai("harga_utama")
    kode = kode_wilayah()
    pihps = baca("pihps_jabar_*.csv", "pihps")
    sp2kp = baca("sp2kp_jabar_*.csv", "sp2kp")

    gabung: dict[tuple[str, str, str], dict] = {}
    gabung.update(sp2kp)   # tambalan lebih dulu
    gabung.update(pihps)   # lalu ditimpa PIHPS bila ada

    baris = []
    for (tanggal, wilayah, komoditas), r in gabung.items():
        baris.append(
            {
                "tanggal": tanggal,
                "kode_kemendagri": kode.get(wilayah, ""),
                "wilayah": wilayah,
                "komoditas": komoditas,
                "harga_rp": r["harga_rp"],
                "sumber": r["sumber"],
                "jenis_harga": r["jenis_harga"],
            }
        )
    baris.sort(key=lambda d: (d["tanggal"], d["wilayah"], d["komoditas"]))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["tanggal", "kode_kemendagri", "wilayah", "komoditas",
                                           "harga_rp", "sumber", "jenis_harga"])
        w.writeheader()
        w.writerows(baris)

    dari = {s: sum(1 for r in baris if r["sumber"] == s) for s in ("pihps", "sp2kp")}
    jenis = {j: sum(1 for r in baris if r["jenis_harga"] == j) for j in ("pasar", "acuan")}
    print(f"ok: {len(baris)} baris -> {OUT.name} ({OUT.stat().st_size // 1024} KB)")
    print(f"  sumber     : {dari}")
    print(f"  jenis_harga: {jenis}")
    print(f"  wilayah    : {len({r['wilayah'] for r in baris})}")
    runlog.selesai(ctx, status="ok", berkas=OUT, jumlah_baris=len(baris))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
