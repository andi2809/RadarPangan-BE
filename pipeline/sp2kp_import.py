"""Impor ekspor Tabulasi Harga SP2KP (Tableau) -> snapshot kanonik.

Tableau pada sp2kp.kemendag.go.id TIDAK menyediakan REST publik (token-nya bukan PAT).
Jalur yang sah: ekspor manual (Download → Crosstab → CSV) lalu impor dengan skrip ini.

    python3 pipeline/sp2kp_import.py --berkas ~/uploads/sp2kp-jabar-2026-10-26.csv

Kolom yang dikenali (fleksibel, huruf besar/kecil tidak masalah):
    Provinsi, Kabupaten/Kota (atau Kabupaten Kota / Wilayah), Komoditas,
    HET/HA (diabaikan), dan satu kolom tanggal berisi harga (mis. 26/10/2026).

Keluaran: data/raw/sp2kp_jabar_<tanggal>.csv
"""

from __future__ import annotations

import argparse
import csv
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import runlog  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
REF = ROOT / "data" / "referensi" / "umk_jabar_2026.csv"

KOMODITAS = {
    "bawang merah": "bawang_merah",
    "beras medium": "beras_medium",
    "cabai rawit merah": "cabai_rawit_merah",
    "telur ayam ras": "telur_ayam_ras",
    "minyakita": "minyakita",
    "minyak goreng curah": "minyak_goreng_curah",
}


def _kunci(teks: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (teks or "").lower()).strip()


def _angka(teks) -> float | None:
    """'12.813' -> 12813 ; '12,813.50' -> 12813.5 ; '' / '-' -> None."""
    s = str(teks or "").strip().replace("Rp", "").strip()
    if not s or s in {"-", "–", "nan"}:
        return None
    if "." in s and "," in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        kiri, kanan = s.rsplit(",", 1)
        s = s.replace(",", "") if len(kanan) == 3 else s.replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(\.\d{3})+", s):
        s = s.replace(".", "")
    try:
        return float(s)
    except ValueError:
        return None


def _tanggal(kolom: str) -> str | None:
    m = re.fullmatch(r"\s*(\d{1,2})/(\d{1,2})/(\d{4})\s*", kolom)
    if not m:
        return None
    hari, bulan, tahun = m.groups()
    return f"{tahun}-{bulan.zfill(2)}-{hari.zfill(2)}"


def _wilayah_sah() -> set[str]:
    with REF.open(encoding="utf-8") as fh:
        return {r["nama_wilayah"] for r in csv.DictReader(fh)}


def baca(berkas: pathlib.Path) -> list[dict]:
    teks = berkas.read_text(encoding="utf-8-sig", errors="replace")
    contoh = teks[:2000].replace(";", ",")
    pembaca = csv.Sniffer().sniff(contoh, delimiters=",;\t") if "," in contoh or ";" in contoh else csv.excel
    baris = list(csv.reader(teks.splitlines(), pembaca))
    if not baris:
        return []

    kepala = baris[0]
    idx_wilayah = next((i for i, k in enumerate(kepala) if "kabupaten" in _kunci(k) or _kunci(k) == "wilayah"), None)
    idx_komoditas = next((i for i, k in enumerate(kepala) if "komoditas" in _kunci(k)), None)
    idx_provinsi = next((i for i, k in enumerate(kepala) if "provinsi" in _kunci(k)), None)
    idx_tanggal = next((i for i, k in enumerate(kepala) if _tanggal(k)), None)

    if idx_wilayah is None or idx_komoditas is None or idx_tanggal is None:
        raise SystemExit(f"Kolom wajib tidak ditemukan di {berkas.name}. Kepala: {kepala}")

    tanggal = _tanggal(kepala[idx_tanggal])
    sah = _wilayah_sah()
    hasil = []
    for row in baris[1:]:
        if len(row) <= max(idx_wilayah, idx_komoditas, idx_tanggal):
            continue
        if idx_provinsi is not None and "jawa barat" not in _kunci(row[idx_provinsi]):
            continue
        wilayah = row[idx_wilayah].strip()
        if wilayah not in sah:
            continue
        kode = KOMODITAS.get(_kunci(row[idx_komoditas]))
        harga = _angka(row[idx_tanggal])
        if not kode or not harga:
            continue
        hasil.append({"tanggal": tanggal, "wilayah": wilayah, "komoditas": kode,
                      "harga_rp": int(round(harga)), "sumber": "sp2kp_kemendag"})
    return hasil


def main() -> int:
    ap = argparse.ArgumentParser(description="Impor ekspor Tabulasi Harga SP2KP (CSV)")
    ap.add_argument("--berkas", required=True, help="CSV hasil ekspor Tableau")
    ap.add_argument("--keluar", default=None, help="direktori keluaran (default: data/raw)")
    args = ap.parse_args()

    berkas = pathlib.Path(args.berkas).expanduser()
    if not berkas.is_file():
        raise SystemExit(f"berkas tidak ada: {berkas}")
    if berkas.suffix.lower() in {".xlsx", ".xls"}:
        raise SystemExit("Simpan ekspor sebagai CSV dulu (Tableau: Download → Crosstab → CSV).")

    ctx = None if args.keluar else runlog.mulai("sp2kp_kemendag")
    data = baca(berkas)
    if not data:
        if ctx:
            runlog.selesai(ctx, status="kosong", pesan="tidak ada baris yang cocok")
        print("Tidak ada baris yang cocok — periksa nama kolom & nama wilayah.")
        return 1

    tanggal = sorted({d["tanggal"] for d in data})[-1]
    folder = pathlib.Path(args.keluar).expanduser() if args.keluar else RAW
    tujuan = folder / f"sp2kp_jabar_{tanggal}.csv"
    tujuan.parent.mkdir(parents=True, exist_ok=True)
    with tujuan.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["tanggal", "wilayah", "komoditas", "harga_rp", "sumber"])
        w.writeheader()
        w.writerows(sorted(data, key=lambda d: (d["wilayah"], d["komoditas"])))

    wilayah = sorted({d["wilayah"] for d in data})
    komoditas = sorted({d["komoditas"] for d in data})
    print(f"ok: {len(data)} baris -> {tujuan.name}")
    print(f"  tanggal : {tanggal}")
    print(f"  wilayah : {len(wilayah)} ({', '.join(wilayah[:4])}{'…' if len(wilayah) > 4 else ''})")
    print(f"  komoditas: {', '.join(komoditas)}")
    if ctx:
        runlog.selesai(ctx, status="ok", berkas=tujuan, jumlah_baris=len(data))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
