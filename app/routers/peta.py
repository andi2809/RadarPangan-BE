import csv
from pathlib import Path
from typing import List, Optional, Literal

from fastapi import APIRouter, Query

from app.schemas import AcuanType, EnvelopeResponse, Meta, PriceStatus, StatusPetaItem
from app.services import harga as harga_service

router = APIRouter(prefix="/api/v1/peta", tags=["Peta"])

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
REF_DIR = DATA_DIR / "referensi"

# Acuan resmi (lihat data/referensi/het_hap.csv)
ACUAN: dict[str, tuple[int, AcuanType]] = {
    "beras_medium": (13500, "HET"),
    "cabai_rawit_merah": (45000, "HAP"),
    "bawang_merah": (32000, "HAP"),
    "telur_ayam_ras": (29500, "DINAMIS_MEDIAN_90H"),
    "minyakita": (15700, "HET"),
}


def _normalize_commodity_code(code: str) -> str:
    return "minyakita" if code == "minyak_goreng_curah" else code


def _status_dari_selisih(selisih: Optional[float]) -> PriceStatus:
    """Ambang terkunci: aman ±5%, waspada >5–10%, kritis >10%, turun < −5%."""
    if selisih is None:
        return "tidak_ada_data"
    if selisih > 10:
        return "kritis"
    if selisih > 5:
        return "waspada"
    if selisih < -5:
        return "turun"
    return "aman"


def _item_kosong(kode: str, nama: str, komoditas: str, acuan: int, jenis: AcuanType) -> StatusPetaItem:
    return StatusPetaItem(
        region_id=kode,
        region_name=nama,
        commodity_id=komoditas,
        harga_aktual_rp=None,
        harga_prediksi_h7_rp=None,
        harga_acuan_rp=acuan,
        jenis_acuan=jenis,
        selisih_persen=None,
        status="tidak_ada_data",
        ews_score=None,
        status_neraca=None,
        kode_kemendagri=kode,
        nama=nama,
        skor_ews=None,
    )


@router.get("/status", response_model=EnvelopeResponse[List[StatusPetaItem]])
async def get_peta_status(
    komoditas: str = Query("beras_medium", description="ID komoditas kanonik"),
    tanggal: Optional[str] = Query(None, description="Tanggal observasi YYYY-MM-DD"),
    layer: Literal["aktual", "h7"] = Query("aktual", description="Lapisan visualisasi data (aktual | h7)"),
):
    """Status harga + skor EWS untuk 27 kab/kota Jawa Barat.

    Harga diambil dari snapshot PIHPS (`data/raw/pihps_jabar_*.csv`).
    Wilayah tanpa data dikembalikan `status="tidak_ada_data"` — tidak dikarang.
    """
    komoditas_kanonik = _normalize_commodity_code(komoditas)
    acuan, jenis_acuan = ACUAN.get(komoditas_kanonik, (13500, "HET"))

    items: List[StatusPetaItem] = []
    csv_path = REF_DIR / "umk_jabar_2026.csv"
    if not csv_path.exists():
        return EnvelopeResponse(
            data=items,
            meta=Meta(mode_data="demo", peringatan_kualitas=["REFERENSI_WILAYAH_TIDAK_ADA"]),
        )

    with csv_path.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            kode = row["kode_kemendagri"]
            nama = row["nama_wilayah"]

            titik = harga_service.terakhir(nama, komoditas_kanonik)
            if titik is None:
                items.append(_item_kosong(kode, nama, komoditas_kanonik, acuan, jenis_acuan))
                continue

            tanggal_data, harga = titik
            if tanggal and tanggal != tanggal_data:
                items.append(_item_kosong(kode, nama, komoditas_kanonik, acuan, jenis_acuan))
                continue

            # Prakiraan H+7: tren linear dari 3 titik terakhir (baseline, bukan ML).
            seri = harga_service.seri(nama, komoditas_kanonik, limit=3)
            if len(seri) >= 2 and seri[0][1] > 0:
                laju = (seri[-1][1] - seri[0][1]) / max(1, len(seri) - 1) / seri[0][1]
            else:
                laju = 0.0
            proyeksi = round(harga * (1 + laju * 7))

            harga_tampil = proyeksi if layer == "h7" else harga
            selisih = round((harga_tampil - acuan) / acuan * 100, 2)
            status = _status_dari_selisih(selisih)
            ews = min(100, max(0, int(50 + selisih * 2)))

            items.append(
                StatusPetaItem(
                    region_id=kode,
                    region_name=nama,
                    commodity_id=komoditas_kanonik,
                    harga_aktual_rp=harga,
                    harga_prediksi_h7_rp=proyeksi,
                    harga_acuan_rp=acuan,
                    jenis_acuan=jenis_acuan,
                    selisih_persen=selisih,
                    status=status,
                    ews_score=ews,
                    status_neraca=None,
                    kode_kemendagri=kode,
                    nama=nama,
                    skor_ews=ews,
                )
            )

    cak = harga_service.cakupan()
    peringatan = ["DATA_PIHPS_SNAPSHOT"] if cak["sumber"] else ["SNAPSHOT_PIHPS_TIDAK_ADA"]
    if cak["jumlah_wilayah"] and cak["jumlah_wilayah"] < 27:
        peringatan.append(f"CAKUPAN_SEBAGIAN_{cak['jumlah_wilayah']}_DARI_27_WILAYAH")

    return EnvelopeResponse(
        data=items,
        meta=Meta(
            tanggal_data=cak["periode"][1] if cak["periode"] else None,
            sumber=["PIHPS BI"],
            mode_data="nyata" if cak["sumber"] else "demo",
            peringatan_kualitas=peringatan,
        ),
    )
