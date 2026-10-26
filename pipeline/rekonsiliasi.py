"""Rekonsiliasi lintas sumber: PIHPS (kab/kota) vs SP2KP Kemendag (provinsi).

Untuk tanggal dan komoditas yang tersedia di dua sumber, hitung selisih antara
median harga kab/kota kita dengan harga provinsi dari SP2KP. Hasilnya disimpan
sebagai `data/derived/rekonsiliasi_<tanggal>.json` dan dicatat di `runs.jsonl`.

Cara pakai:
    python3 pipeline/rekonsiliasi.py --tanggal 2026-10-26
"""

from __future__ import annotations

import argparse
import json
import pathlib
import statistics
import sys
import urllib.request
from datetime import date

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import runlog  # noqa: E402
import pihps_fetch  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services import harga as harga_service  # noqa: E402

API = "https://api-sp2kp.kemendag.go.id"
PROV_JABAR = "32"
UA = {"User-Agent": "RadarPangan/1.0 (riset lomba)"}

# komoditas kita -> variant_id SP2KP
VARIAN = {
    "beras_medium": 52,
    "cabai_rawit_merah": 10,
    "bawang_merah": 13,
    "telur_ayam_ras": 25,
    "minyak_goreng_curah": 16,
}

AMBANG_SELISIH = {"sehat": 10.0, "waspada": 25.0}


def _get(path: str) -> dict:
    req = urllib.request.Request(API + path, headers=UA)
    with urllib.request.urlopen(req, timeout=40) as resp:
        return json.loads(resp.read().decode())


def harga_provinsi(tanggal: str, variant_id: int) -> float | None:
    data = _get(f"/report/api/average-price/province-comparison?tanggal={tanggal}&variant_id={variant_id}")
    for item in (data.get("data") or {}).get("items", []):
        if str(item.get("kode_provinsi")) == PROV_JABAR:
            harga = item.get("harga")
            return round(float(harga), 2) if isinstance(harga, (int, float)) else None
    return None


def _angka_pihps(nilai) -> float:
    """'15,850' -> 15850 (koma = ribuan); '15.850,00' -> 15850.0 (gaya Indonesia)."""
    teks = str(nilai).strip()
    if "." in teks and "," in teks:
        teks = teks.replace(".", "").replace(",", ".")
    elif "," in teks:
        kiri, kanan = teks.rsplit(",", 1)
        teks = teks.replace(",", "") if len(kanan) == 3 else teks.replace(",", ".")
    return float(teks)


def harga_provinsi_pihps(komoditas: str, tanggal: str) -> float | None:
    """Harga level provinsi dari PIHPS sendiri (pembanding spasial sumber yang sama)."""
    kode = pihps_fetch.peta_komoditas().get(komoditas)
    if not kode:
        return None
    pihps_fetch._warm_session()
    data = pihps_fetch._get(
        f"/WebSite/TabelHarga/GetGridDataKomoditas?comcat_id={kode}&price_type_id=1"
        f"&province_id={pihps_fetch.JABAR_PROVINCE_ID}&tipe_laporan=1"
        f"&start_date={tanggal}&end_date={tanggal}"
    )
    for row in data.get("data") or []:
        if "jawa barat" not in str(row.get("name", "")).lower():
            continue
        for kunci, nilai in row.items():
            if "/" not in str(kunci):
                continue
            try:
                return round(_angka_pihps(nilai), 2)
            except (TypeError, ValueError):
                return None
    return None


def median_kabkota(tanggal: str, komoditas: str) -> tuple[float | None, int]:
    nilai = []
    for nama in [w for w in _wilayah_list()]:
        titik = harga_service.seri(nama, komoditas)
        cocok = [h for t, h in titik if t == tanggal]
        if cocok:
            nilai.append(cocok[-1])
    if not nilai:
        return None, 0
    return round(statistics.median(nilai), 2), len(nilai)


def _wilayah_list() -> list[str]:
    import csv

    path = ROOT / "data" / "referensi" / "umk_jabar_2026.csv"
    with path.open(encoding="utf-8") as fh:
        return [r["nama_wilayah"] for r in csv.DictReader(fh)]


def klasifikasi(selisih: float | None) -> str:
    if selisih is None:
        return "tidak_dapat_dibandingkan"
    mutlak = abs(selisih)
    if mutlak <= AMBANG_SELISIH["sehat"]:
        return "sehat"
    if mutlak <= AMBANG_SELISIH["waspada"]:
        return "waspada"
    return "perlu_ditinjau"


def main() -> int:
    ap = argparse.ArgumentParser(description="Rekonsiliasi PIHPS vs SP2KP")
    ap.add_argument("--tanggal", default=None, help="YYYY-MM-DD (default: tanggal terakhir snapshot)")
    args = ap.parse_args()

    cak = harga_service.cakupan()
    tanggal = args.tanggal or (cak["periode"][1] if cak["periode"] else date.today().isoformat())

    ctx = runlog.mulai("sp2kp_kemendag")
    baris = []
    for komoditas, vid in VARIAN.items():
        median, jumlah = median_kabkota(tanggal, komoditas)
        try:
            prov = harga_provinsi(tanggal, vid)
        except Exception as exc:  # jaringan/404: jangan gagalkan seluruh laporan
            prov = None
            print(f"  ! {komoditas}: gagal ambil SP2KP ({exc})")

        try:
            prov_pihps = harga_provinsi_pihps(komoditas, tanggal)
        except Exception as exc:
            prov_pihps = None
            print(f"  ! {komoditas}: gagal ambil provinsi PIHPS ({exc})")

        selisih = None
        if median and prov:
            selisih = round((median - prov) / prov * 100, 2)
        selisih_pihps = None
        if median and prov_pihps:
            selisih_pihps = round((median - prov_pihps) / prov_pihps * 100, 2)

        baris.append(
            {
                "komoditas": komoditas,
                "variant_id_sp2kp": vid,
                "pihps_median_kabkota_rp": median,
                "pihps_jumlah_wilayah": jumlah,
                "sp2kp_provinsi_rp": prov,
                "pihps_provinsi_rp": prov_pihps,
                "selisih_vs_pihps_provinsi_persen": selisih_pihps,
                "selisih_persen": selisih,
                "status": klasifikasi(selisih),
            }
        )
        print(f"  {komoditas:20s} median={median} (n={jumlah})  provSP2KP={prov} ({selisih}%)  provPIHPS={prov_pihps} ({selisih_pihps}%)")

    tujuan = ROOT / "data" / "derived" / f"rekonsiliasi_{tanggal}.json"
    tujuan.parent.mkdir(parents=True, exist_ok=True)
    tujuan.write_text(
        json.dumps(
            {
                "tanggal": tanggal,
                "metode": "median harga kab/kota (PIHPS) dibanding harga provinsi Jawa Barat (SP2KP)",
                "ambang": AMBANG_SELISIH,
                "catatan": "Selisih bukan error data; ini mengukur perbedaan cakupan pasar kab/kota vs agregat provinsi.",
                "komoditas": baris,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"selesai -> {tujuan}")
    runlog.selesai(ctx, status="ok", berkas=tujuan, jumlah_baris=len(baris))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
