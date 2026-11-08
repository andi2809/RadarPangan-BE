"""Impor dataset harga Bapanas (Excel) menjadi CSV kanonik untuk API.

Sumber: surat Badan Pangan Nasional No. 1014/TS.02.03/B.2/11/2026 — berkas
`bapanas_jabar_*.xlsx` berisi dua sheet: "Produsen" dan "Konsumen".

Keluaran: data/paket/bapanas.csv.gz
Kolom  : tanggal, wilayah, kode_kemendagri, komoditas, tingkat, harga_rp, sumber

Catatan kepatuhan: berkas Excel asli **tidak** disimpan di repo (repo akan publik).
Berkas mentah berada di `dokumen/data-bapanas-privat/` dan hanya turunannya
yang dipublikasikan, dengan atribusi ke Badan Pangan Nasional.
"""

from __future__ import annotations

import csv
import gzip
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import runlog  # noqa: E402

SUMBER_XLSX = pathlib.Path.home() / "lomba/web-in-action-2026/dokumen/data-bapanas-privat"
REF = ROOT / "data" / "referensi" / "umk_jabar_2026.csv"
OUT = ROOT / "data" / "paket" / "bapanas.csv.gz"

KOLOM = ["tanggal", "wilayah", "kode_kemendagri", "komoditas", "tingkat", "harga_rp", "sumber"]

PETA_KONSUMEN = {
    "beras medium": "beras_medium",
    "bawang merah": "bawang_merah",
    "cabai rawit merah": "cabai_rawit_merah",
    "telur ayam ras": "telur_ayam_ras",
    "minyak goreng curah": "minyak_goreng_curah",
    "minyak goreng kemasan": "minyak_goreng_kemasan",
}
PETA_PRODUSEN = {
    "beras medium tingkat penggilingan": "beras_medium",
    "bawang merah tingkat petani": "bawang_merah",
    "cabai rawit merah tingkat petani2": "cabai_rawit_merah",
    "telur ayam ras": "telur_ayam_ras",
}


def _kode_wilayah() -> dict[str, str]:
    with REF.open(encoding="utf-8") as fh:
        return {r["nama_wilayah"].strip().lower(): r["kode_kemendagri"] for r in csv.DictReader(fh)}


def _angka(nilai) -> int | None:
    if nilai is None:
        return None
    teks = str(nilai).strip().replace(".", "").replace(",", ".") if isinstance(nilai, str) else nilai
    try:
        angka = float(teks)
    except (TypeError, ValueError):
        return None
    return int(round(angka)) if angka > 0 else None


def _baca_sheet(wb, nama: str, peta: dict[str, str], tingkat: str) -> list[dict]:
    asli = {n.strip().lower(): n for n in wb.sheetnames}
    ws = wb[asli[nama.strip().lower()]]
    baris = list(ws.iter_rows(values_only=True))
    kepala = [str(c).strip().lower() if c else "" for c in baris[4]]
    kolom = {i: peta[h] for i, h in enumerate(kepala) if h in peta}
    if not kolom:
        raise SystemExit(f"kolom komoditas tidak dikenali di sheet {nama}")
    hasil = []
    for r in baris[5:]:
        tanggal = str(r[2])[:10] if r[2] else ""
        wilayah = str(r[1]).strip() if r[1] else ""
        if not tanggal or not wilayah:
            continue
        for i, komoditas in kolom.items():
            harga = _angka(r[i])
            if harga is None:
                continue
            hasil.append({"tanggal": tanggal, "wilayah": wilayah, "komoditas": komoditas,
                          "tingkat": tingkat, "harga_rp": harga})
    return hasil


def main() -> int:
    berkas = sorted(SUMBER_XLSX.glob("bapanas_jabar_*.xlsx"))
    if not berkas:
        print(f"berkas Excel tidak ditemukan di {SUMBER_XLSX}", file=sys.stderr)
        return 1
    try:
        import openpyxl
    except ImportError:
        print("butuh openpyxl: pip install openpyxl", file=sys.stderr)
        return 1

    ctx = runlog.mulai("bapanas_import")
    kode = _kode_wilayah()
    wb = openpyxl.load_workbook(berkas[0], read_only=True, data_only=True)
    data = _baca_sheet(wb, "Konsumen", PETA_KONSUMEN, "konsumen")
    data += _baca_sheet(wb, "Produsen", PETA_PRODUSEN, "produsen")

    bersih = []
    tanpa_kode = 0
    for r in data:
        kunci = r["wilayah"].lower()
        if kunci == "jawa barat":          # agregat provinsi, bukan kab/kota
            continue
        kode_wilayah = kode.get(kunci, "")
        if not kode_wilayah:
            tanpa_kode += 1
            continue
        bersih.append({**r, "kode_kemendagri": kode_wilayah, "sumber": "bapanas"})

    bersih.sort(key=lambda d: (d["tanggal"], d["wilayah"], d["komoditas"], d["tingkat"]))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(OUT, "wt", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=KOLOM)
        w.writeheader()
        w.writerows(bersih)

    wilayah = len({r["kode_kemendagri"] for r in bersih})
    konsumen = sum(1 for r in bersih if r["tingkat"] == "konsumen")
    print(f"ok: {len(bersih)} baris -> {OUT.name} ({OUT.stat().st_size / 1e6:.2f} MB)")
    print(f"  wilayah {wilayah} · konsumen {konsumen} · produsen {len(bersih) - konsumen} · tanpa kode {tanpa_kode}")
    runlog.selesai(ctx, status="ok", berkas=OUT, jumlah_baris=len(bersih))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
