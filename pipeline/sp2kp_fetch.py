"""Tarik Statistik Harian SP2KP per kabupaten/kota (otomasi endpoint aplikasi).

Endpoint: POST /report/api/average-price/export-area-daily-excel (multipart)
    start_date, end_date, level=2, variant_ids, kode_provinsi=32,
    kode_kab_kota=<kode BPS>, pasar_id=, skip_sat_sun=true, tipe_komoditas=1

level=1 -> agregat provinsi; level=2 -> per kab/kota (wajib kode_kab_kota);
level=3 -> per pasar (wajib pasar_id).

    python3 pipeline/sp2kp_fetch.py --start 2026-10-26 --end 2026-10-26
"""

from __future__ import annotations

import argparse
import csv
import pathlib
import sys
import time

import httpx

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import runlog  # noqa: E402
import sp2kp_import as imp  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
REF = ROOT / "data" / "referensi" / "umk_jabar_2026.csv"

URL = "https://api-sp2kp.kemendag.go.id/report/api/average-price/export-area-daily-excel"
VARIAN = {"52": "beras_medium", "10": "cabai_rawit_merah", "13": "bawang_merah",
          "18": "minyakita", "25": "telur_ayam_ras"}
KEPALA = {"Accept": "application/json", "Origin": "https://sp2kp.kemendag.go.id",
          "Referer": "https://sp2kp.kemendag.go.id/"}


def wilayah() -> list[tuple[str, str]]:
    """(kode_bps, nama_wilayah) dari referensi 27 kab/kota."""
    with REF.open(encoding="utf-8") as fh:
        return [(r["kode_bps"], r["nama_wilayah"]) for r in csv.DictReader(fh)]


def tarik(kode: str, start: str, end: str, timeout: float = 60.0) -> list[dict]:
    data = {
        "start_date": start, "end_date": end, "level": "2",
        "variant_ids": ",".join(VARIAN), "kode_provinsi": "32",
        "kode_kab_kota": kode, "pasar_id": "", "skip_sat_sun": "true",
        "tipe_komoditas": "1",
    }
    r = httpx.post(URL, data=data, headers=KEPALA, timeout=timeout,
                   files={k: (None, v) for k, v in data.items()})
    r.raise_for_status()
    if not r.content.startswith(b"PK"):
        raise RuntimeError(f"respons bukan xlsx: {r.content[:120]!r}")

    baris = _xlsx(r.content)
    if len(baris) < 4:
        return []

    kepala = baris[2]
    kolom_tanggal = {i: c for i, c in enumerate(kepala) if imp._tanggal(str(c))}
    hasil = []
    for row in baris[3:]:
        if not row:
            continue
        kode_kom = imp.KOMODITAS.get(imp._kunci(row[0]))
        if not kode_kom:
            continue
        for i, tanggal_mentah in kolom_tanggal.items():
            if i >= len(row):
                continue
            harga = imp._angka(row[i])
            if harga:
                hasil.append({"tanggal": imp._tanggal(str(tanggal_mentah)),
                              "komoditas": kode_kom, "harga_rp": int(round(harga))})
    return hasil


def _xlsx(blob: bytes) -> list[list[str]]:
    """Baca xlsx dari bytes (sp2kp_import.baca_xlsx butuh path)."""
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".xlsx") as tmp:
        tmp.write(blob)
        tmp.flush()
        return imp.baca_xlsx(pathlib.Path(tmp.name))


def main() -> int:
    ap = argparse.ArgumentParser(description="Tarik Statistik Harian SP2KP per kab/kota")
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--kode", default=None, help="batasi ke satu/lebih kode BPS (uji cepat)")
    ap.add_argument("--jeda", type=float, default=1.0, help="jeda antar wilayah (detik)")
    args = ap.parse_args()

    daftar = wilayah()
    if args.kode:
        ingin = {k.strip() for k in args.kode.split(",")}
        daftar = [w for w in daftar if w[0] in ingin]

    ctx = runlog.mulai("sp2kp_kemendag")
    hasil: list[dict] = []
    gagal = []
    for kode, nama in daftar:
        try:
            titik = tarik(kode, args.start, args.end)
        except Exception as exc:
            gagal.append(f"{kode} {nama}: {exc}")
            print(f"  ! {nama}: {exc}")
            continue
        for t in titik:
            t["wilayah"] = nama
            t["sumber"] = "sp2kp_kemendag"
        hasil.extend(titik)
        print(f"  {nama:20s} {len(titik):3d} titik")
        time.sleep(args.jeda)

    if not hasil:
        runlog.selesai(ctx, status="kosong", pesan="; ".join(gagal)[:300])
        print("tidak ada data")
        return 1

    tujuan = RAW / f"sp2kp_jabar_{args.start}_{args.end}.csv"
    tujuan.parent.mkdir(parents=True, exist_ok=True)
    with tujuan.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["tanggal", "wilayah", "komoditas", "harga_rp", "sumber"])
        w.writeheader()
        w.writerows(sorted(hasil, key=lambda d: (d["tanggal"], d["wilayah"], d["komoditas"])))

    wilayah_ada = len({h["wilayah"] for h in hasil})
    print(f"\nselesai: {len(hasil)} baris, {wilayah_ada}/{len(daftar)} wilayah -> {tujuan.name}")
    if gagal:
        print(f"gagal: {len(gagal)} wilayah (lihat log)")
    runlog.selesai(ctx, status="ok", berkas=tujuan, jumlah_baris=len(hasil),
                   pesan="; ".join(gagal)[:300])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
