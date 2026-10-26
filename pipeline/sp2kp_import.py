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
import re as _re
import zipfile
from xml.etree import ElementTree as ET
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
    """Terima 'dd/mm/yyyy' (ekspor UI) maupun 'yyyy-mm-dd' (ekspor API)."""
    teks = str(kolom).strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", teks):
        return teks
    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", teks)
    if not m:
        return None
    hari, bulan, tahun = m.groups()
    return f"{tahun}-{bulan.zfill(2)}-{hari.zfill(2)}"


def _wilayah_sah() -> set[str]:
    with REF.open(encoding="utf-8") as fh:
        return {r["nama_wilayah"] for r in csv.DictReader(fh)}


NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def _kolom(ref: str) -> int:
    huruf = _re.match(r"([A-Z]+)", ref or "A").group(1)
    nilai = 0
    for ch in huruf:
        nilai = nilai * 26 + (ord(ch) - 64)
    return nilai - 1


def baca_xlsx(berkas: pathlib.Path) -> list[list[str]]:
    """Pembaca xlsx minimal (stdlib): sharedStrings + sheet pertama."""
    with zipfile.ZipFile(berkas) as z:
        nama = set(z.namelist())

        bersama: list[str] = []
        if "xl/sharedStrings.xml" in nama:
            akar = ET.fromstring(z.read("xl/sharedStrings.xml"))
            for si in akar.findall("m:si", NS):
                bersama.append("".join(t.text or "" for t in si.iter(f"{{{NS['m']}}}t")))

        # Pilih worksheet dengan isi terbanyak (berkas ekspor sering punya sheet kosong).
        kandidat = sorted(n for n in nama if n.startswith("xl/worksheets/sheet") and n.endswith(".xml"))
        if not kandidat:
            raise SystemExit(f"tidak ada worksheet di {berkas.name}")
        sheet, terbaik = kandidat[0], -1
        for calon in kandidat:
            try:
                jumlah = len(ET.fromstring(z.read(calon)).findall(".//m:sheetData/m:row", NS))
            except ET.ParseError:
                continue
            if jumlah > terbaik:
                sheet, terbaik = calon, jumlah

        akar = ET.fromstring(z.read(sheet))
        hasil: list[list[str]] = []
        for row in akar.findall(".//m:sheetData/m:row", NS):
            sel: dict[int, str] = {}
            for c in row.findall("m:c", NS):
                idx = _kolom(c.get("r", "A1"))
                tipe = c.get("t")
                if tipe == "s":
                    v = c.find("m:v", NS)
                    sel[idx] = bersama[int(v.text)] if v is not None and v.text else ""
                elif tipe == "inlineStr":
                    sel[idx] = "".join(x.text or "" for x in c.iter(f"{{{NS['m']}}}t"))
                else:
                    v = c.find("m:v", NS)
                    sel[idx] = v.text if v is not None and v.text else ""
            lebar = max(sel) + 1 if sel else 0
            hasil.append([sel.get(i, "") for i in range(lebar)])
        return hasil


def baca(berkas: pathlib.Path) -> list[dict]:
    if berkas.suffix.lower() in {".xlsx", ".xlsm"}:
        return _dari_baris(baca_xlsx(berkas))
    return _dari_csv(berkas)


def _dari_baris(baris: list[list[str]]) -> list[dict]:
    class _P:
        pass
    p = _P(); p.baris = baris
    return _parse_baris(baris)


def _dari_csv(berkas: pathlib.Path) -> list[dict]:
    teks = berkas.read_text(encoding="utf-8-sig", errors="replace")
    contoh = teks[:2000].replace(";", ",")
    pembaca = csv.Sniffer().sniff(contoh, delimiters=",;\t") if "," in contoh or ";" in contoh else csv.excel
    return _parse_baris(list(csv.reader(teks.splitlines(), pembaca)))


def _parse_baris(baris: list[list[str]]) -> list[dict]:
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
    if berkas.suffix.lower() == ".xls":
        raise SystemExit("Format .xls lama belum didukung — simpan ulang sebagai .xlsx atau CSV.")

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
