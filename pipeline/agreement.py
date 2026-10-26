"""Kesepakatan dua seri: Spearman, bias, dan limit of agreement (Bland–Altman).

Membandingkan median 9 kab/kota (PIHPS) dengan seri provinsi Jawa Barat (PIHPS)
untuk rentang tanggal yang sama. Semua data resmi, tanpa verifikasi lapangan.

    python3 pipeline/agreement.py
"""

from __future__ import annotations

import csv
import json
import pathlib
import statistics
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import runlog  # noqa: E402
import pihps_fetch  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services import harga as harga_service  # noqa: E402

KOMODITAS = ["beras_medium", "cabai_rawit_merah", "bawang_merah", "telur_ayam_ras", "minyak_goreng_curah"]


def _wilayah() -> list[str]:
    with (ROOT / "data" / "referensi" / "umk_jabar_2026.csv").open(encoding="utf-8") as fh:
        return [r["nama_wilayah"] for r in csv.DictReader(fh)]


def _provinsi_seri(komoditas: str) -> dict[str, float]:
    kode = pihps_fetch.peta_komoditas().get(komoditas)
    if not kode:
        return {}
    pihps_fetch._warm_session()
    data = pihps_fetch._get(
        f"/WebSite/TabelHarga/GetGridDataKomoditas?comcat_id={kode}&price_type_id=1"
        f"&province_id={pihps_fetch.JABAR_PROVINCE_ID}&tipe_laporan=1"
        f"&start_date=2026-08-01&end_date=2026-10-26"
    )
    for baris in data.get("data") or []:
        if "jawa barat" not in str(baris.get("name", "")).lower():
            continue
        hasil = {}
        for kunci, nilai in baris.items():
            if "/" not in str(kunci):
                continue
            hari, bulan, tahun = str(kunci).split("/")
            iso = f"{tahun}-{bulan.zfill(2)}-{hari.zfill(2)}"
            try:
                hasil[iso] = pihps_fetch_angka(nilai)
            except (TypeError, ValueError):
                continue
        return hasil
    return {}


def pihps_fetch_angka(nilai) -> float:
    teks = str(nilai).strip()
    if "." in teks and "," in teks:
        teks = teks.replace(".", "").replace(",", ".")
    elif "," in teks:
        kiri, kanan = teks.rsplit(",", 1)
        teks = teks.replace(",", "") if len(kanan) == 3 else teks.replace(",", ".")
    return float(teks)


def _peringkat(nilai: list[float]) -> list[float]:
    urut = sorted(range(len(nilai)), key=lambda i: nilai[i])
    pangkat = [0.0] * len(nilai)
    for posisi, indeks in enumerate(urut, 1):
        pangkat[indeks] = float(posisi)
    return pangkat


def spearman(a: list[float], b: list[float]) -> float | None:
    if len(a) < 3:
        return None
    ra, rb = _peringkat(a), _peringkat(b)
    ma, mb = statistics.mean(ra), statistics.mean(rb)
    pembilang = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    penyebut = (sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb)) ** 0.5
    return round(pembilang / penyebut, 3) if penyebut else None


def bland_altman(kita: list[float], acuan: list[float]) -> dict:
    selisih = [k - a for k, a in zip(kita, acuan)]
    bias = statistics.mean(selisih)
    sd = statistics.stdev(selisih) if len(selisih) > 1 else 0.0
    return {
        "bias_rp": round(bias, 1),
        "simpangan_baku_rp": round(sd, 1),
        "loa_bawah_rp": round(bias - 1.96 * sd, 1),
        "loa_atas_rp": round(bias + 1.96 * sd, 1),
        "n": len(selisih),
    }


def main() -> int:
    ctx = runlog.mulai("agreement_pihps")
    hasil = []
    for komoditas in KOMODITAS:
        prov = _provinsi_seri(komoditas)
        kita = {}
        for wilayah in _wilayah():
            for tanggal, harga in harga_service.seri(wilayah, komoditas):
                kita.setdefault(tanggal, []).append(harga)

        irisan = [t for t in sorted(prov) if t in kita]
        if len(irisan) < 3:
            print(f"{komoditas:20s} data tidak cukup (n={len(irisan)})")
            continue

        seri_kita = [statistics.median(kita[t]) for t in irisan]
        seri_prov = [prov[t] for t in irisan]
        hasil.append(
            {
                "komoditas": komoditas,
                "n_hari": len(irisan),
                "spearman": spearman(seri_kita, seri_prov),
                "bland_altman": bland_altman(seri_kita, seri_prov),
                "median_selisih_persen": round(
                    statistics.median((k - p) / p * 100 for k, p in zip(seri_kita, seri_prov)), 2
                ),
            }
        )
        baris = hasil[-1]
        print(
            f"{komoditas:20s} n={baris['n_hari']:3d} ρ={baris['spearman']} "
            f"bias={baris['bland_altman']['bias_rp']} Rp "
            f"LoA=[{baris['bland_altman']['loa_bawah_rp']}, {baris['bland_altman']['loa_atas_rp']}] "
            f"selisih_median={baris['median_selisih_persen']}%"
        )

    tujuan = ROOT / "data" / "derived" / "agreement_pihps_provinsi.json"
    tujuan.parent.mkdir(parents=True, exist_ok=True)
    tujuan.write_text(json.dumps({
        "metode": "median 9 kab/kota (PIHPS) vs seri provinsi Jawa Barat (PIHPS), hari yang sama",
        "catatan": "Spearman mengukur kesamaan arah; Bland–Altman mengukur bias dan rentang kesepakatan (Rp).",
        "komoditas": hasil,
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n-> {tujuan}")
    runlog.selesai(ctx, status="ok", berkas=tujuan, jumlah_baris=len(hasil))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
