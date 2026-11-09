"""Disparitas harga antarwilayah — sinyal alternatif saat level harga datar.

Untuk komoditas yang harganya menempel acuan (beras, minyak), perubahan level tidak
informatif. Yang masih bisa dibaca: sebaran antar kab/kota pada hari yang sama.

Keluaran: data/derived/disparitas_<sumber>.json
"""

from __future__ import annotations

import csv
import gzip
import json
import pathlib
import statistics
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import runlog  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"


def berkas_terbaru(pola: str) -> pathlib.Path:
    kandidat = sorted(RAW.glob(pola))
    if not kandidat:
        raise SystemExit(f"tidak ada berkas {pola} di {RAW}")
    return kandidat[-1]


def hitung_pihps() -> dict:
    """PIHPS dibaca lewat loader yang menggabungkan semua snapshot (bukan berkas terakhir)."""
    sys.path.insert(0, str(ROOT))
    from app.services import harga as harga_service

    data: dict[tuple[str, str], list[tuple[str, int]]] = {}
    nama_wilayah = []
    with (ROOT / "data" / "referensi" / "umk_jabar_2026.csv").open(encoding="utf-8") as fh:
        nama_wilayah = [r["nama_wilayah"] for r in csv.DictReader(fh)]

    for komoditas in ("beras_medium", "cabai_rawit_merah", "bawang_merah", "telur_ayam_ras", "minyak_goreng_curah"):
        for wilayah in nama_wilayah:
            for tanggal, harga in harga_service.seri(wilayah, komoditas):
                data.setdefault((tanggal, komoditas), []).append((wilayah, harga))
    return _ringkas(data, "pihps (gabungan snapshot)")


def hitung_bapanas() -> dict:
    """Sumber utama: paket Bapanas (konsumen), dibatasi 180 hari terakhir agar berkas tetap ringan."""
    paket = ROOT / "data" / "paket" / "bapanas.csv.gz"
    if not paket.exists():
        raise SystemExit(f"paket tidak ada: {paket}")
    data: dict[tuple[str, str], list[tuple[str, int]]] = {}
    with gzip.open(paket, "rt", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if (row.get("tingkat") or "konsumen") != "konsumen":
                continue
            data.setdefault((row["tanggal"], row["komoditas"]), []).append(
                (row["wilayah"], int(row["harga_rp"]))
            )
    tanggal = sorted({t for t, _ in data})
    potong = tanggal[-180:] if len(tanggal) > 180 else tanggal
    batas = set(potong)
    data = {k: v for k, v in data.items() if k[0] in batas}
    return _ringkas(data, "bapanas (paket konsumen, 180 hari terakhir)")


def hitung(path: pathlib.Path) -> dict:
    data: dict[tuple[str, str], list[tuple[str, int]]] = {}
    with path.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            kunci = (row["tanggal"], row["komoditas"])
            data.setdefault(kunci, []).append((row["wilayah"], int(row["harga_rp"])))

    return _ringkas(data, path.name)


def _ringkas(data: dict, nama: str) -> dict:
    per_komoditas: dict[str, list[dict]] = {}
    for (tanggal, komoditas), isi in sorted(data.items()):
        if len(isi) < 3:
            continue
        harga = [h for _w, h in isi]
        rendah = min(isi, key=lambda x: x[1])
        tinggi = max(isi, key=lambda x: x[1])
        median = statistics.median(harga)
        per_komoditas.setdefault(komoditas, []).append(
            {
                "tanggal": tanggal,
                "n_wilayah": len(isi),
                "terendah": {"wilayah": rendah[0], "harga_rp": rendah[1]},
                "tertinggi": {"wilayah": tinggi[0], "harga_rp": tinggi[1]},
                "median_rp": median,
                "sebaran_rp": tinggi[1] - rendah[1],
                "sebaran_persen": round((tinggi[1] - rendah[1]) / median * 100, 2) if median else None,
            }
        )

    ringkas = {}
    for komoditas, baris in per_komoditas.items():
        sebaran = [b["sebaran_persen"] for b in baris if b["sebaran_persen"] is not None]
        ringkas[komoditas] = {
            "n_hari": len(baris),
            "sebaran_median_persen": round(statistics.median(sebaran), 2) if sebaran else None,
            "sebaran_min_persen": min(sebaran) if sebaran else None,
            "sebaran_max_persen": max(sebaran) if sebaran else None,
            "bergerak": (max(sebaran) - min(sebaran) > 1.0) if sebaran else False,
            "harian": baris,
        }
    return {"berkas": nama, "komoditas": ringkas}


def main() -> int:
    ctx = runlog.mulai("disparitas")
    hasil = {}
    try:
        hasil["bapanas"] = hitung_bapanas()
        print(f"\nBAPANAS ({hasil['bapanas']['berkas']})")
        for kom, r in hasil["bapanas"]["komoditas"].items():
            print(f"  {kom:24s} sebaran median {r['sebaran_median_persen']}%")
    except SystemExit as exc:
        print(f"  ! bapanas: {exc}")

    for label, pola in ():
        try:
            path = berkas_terbaru(pola) if pola else None
        except SystemExit as exc:
            print(f"  ! {label}: {exc}")
            continue
        hasil[label] = hitung(path) if path else hitung_pihps()
        print(f"\n{label.upper()} ({hasil[label]['berkas']})")
        print(f"  {'komoditas':20s} {'sebaran median':>15s} {'min–max':>16s} {'bergerak?':>10s}")
        for kom, r in hasil[label]["komoditas"].items():
            print(
                f"  {kom:20s} {str(r['sebaran_median_persen'])+'%':>15s} "
                f"{str(r['sebaran_min_persen'])+'–'+str(r['sebaran_max_persen'])+'%':>16s} "
                f"{('ya' if r['bergerak'] else 'tidak'):>10s}"
            )

    hasil = {"bapanas": hasil["bapanas"]}
    tujuan = ROOT / "data" / "derived" / "disparitas.json"
    tujuan.parent.mkdir(parents=True, exist_ok=True)
    tujuan.write_text(json.dumps(hasil, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n-> {tujuan}")
    runlog.selesai(ctx, status="ok", berkas=tujuan, jumlah_baris=len(hasil))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
