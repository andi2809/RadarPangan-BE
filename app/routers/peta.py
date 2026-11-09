import csv
from pathlib import Path
from typing import List, Optional, Literal

from fastapi import APIRouter, Query

from app.schemas import AcuanType, EnvelopeResponse, Meta, PriceStatus, StatusPetaItem
from app.services import acuan as acuan_service
from app.services import bapanas as bapanas_service
from app.services import fakta as fakta_service
from app.services import prakiraan as prakiraan_service
from app.services import skor as skor_service
from app.services import harga as harga_service

router = APIRouter(prefix="/api/v1/peta", tags=["Peta"])

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
REF_DIR = DATA_DIR / "referensi"

# Acuan resmi (lihat data/referensi/het_hap.csv)


def _normalize_commodity_code(code: str) -> str:
    return code


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


def _item_kosong(
    kode: str, nama: str, komoditas: str, acuan: int, jenis: AcuanType, sumber: str | None = None
) -> StatusPetaItem:
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
        sumber=sumber,
        jenis_harga=fakta_service.metode_data(sumber) if sumber else None,
    )


@router.get("/status", response_model=EnvelopeResponse[List[StatusPetaItem]])
async def get_peta_status(
    komoditas: str = Query("beras_medium", description="ID komoditas kanonik"),
    tanggal: Optional[str] = Query(None, description="Tanggal observasi YYYY-MM-DD"),
    layer: Literal["aktual", "h7"] = Query("aktual", description="Lapisan visualisasi data (aktual | h7)"),
    sumber: Literal["bapanas", "pihps", "sp2kp", "utama"] = Query(
        "bapanas", description="pihps | sp2kp | utama (PIHPS prioritas, SP2KP menambal)"
    ),
):
    """Status harga + skor EWS untuk 27 kab/kota Jawa Barat.

    Harga diambil dari snapshot PIHPS (`data/raw/pihps_jabar_*.csv`).
    Wilayah tanpa data dikembalikan `status="tidak_ada_data"` — tidak dikarang.
    """
    # Saat dipanggil langsung (bukan lewat HTTP), default parameter masih berupa objek Query.
    sumber = sumber if isinstance(sumber, str) else "bapanas"
    layer = layer if isinstance(layer, str) else "aktual"
    komoditas = komoditas if isinstance(komoditas, str) else "beras_medium"
    komoditas_kanonik = _normalize_commodity_code(komoditas)
    data_acuan = acuan_service.untuk(komoditas_kanonik)
    acuan = data_acuan["acuan_rp"] if data_acuan else 13500
    jenis_acuan = data_acuan["jenis"] if data_acuan else "HET"

    items: List[StatusPetaItem] = []
    tanggal_terbaru: str | None = None
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

            asal = sumber
            if sumber in ("bapanas", "utama") and sumber == "bapanas":
                titik = bapanas_service.terakhir(nama, komoditas_kanonik)
                seri_penuh = bapanas_service.seri(nama, komoditas_kanonik)
            elif sumber == "utama":
                titik = bapanas_service.terakhir(nama, komoditas_kanonik)
                if titik:
                    seri_penuh, asal = bapanas_service.seri(nama, komoditas_kanonik), "bapanas"
                else:
                    hasil_utama = fakta_service.terakhir_utama(nama, komoditas_kanonik)
                    if hasil_utama:
                        titik, asal = hasil_utama
                        seri_penuh = fakta_service.seri(nama, komoditas_kanonik, asal)
                    else:
                        titik, seri_penuh = None, []
            elif sumber == "sp2kp":
                titik = fakta_service.terakhir(nama, komoditas_kanonik, "sp2kp")
                seri_penuh = fakta_service.seri(nama, komoditas_kanonik, "sp2kp")
            else:
                titik = harga_service.terakhir(nama, komoditas_kanonik)
                seri_penuh = harga_service.seri(nama, komoditas_kanonik)
            if titik is None:
                items.append(_item_kosong(kode, nama, komoditas_kanonik, acuan, jenis_acuan, sumber))
                continue

            tanggal_data, harga = titik
            if tanggal_terbaru is None or tanggal_data > tanggal_terbaru:
                tanggal_terbaru = tanggal_data
            if tanggal and tanggal != tanggal_data:
                items.append(_item_kosong(kode, nama, komoditas_kanonik, acuan, jenis_acuan, sumber))
                continue

            # Prakiraan H+7: exponential smoothing + pita 95% (lihat services/prakiraan.py).
            prakiraan = prakiraan_service.prakiraan_h7(
                seri_penuh,
                fakta_service.flat_days(seri_penuh),
                komoditas=komoditas_kanonik,
                sumber=asal,
            )
            if prakiraan:
                proyeksi = prakiraan["harga_prediksi_h7_rp"]
            else:  # data terlalu pendek: jangan mengarang proyeksi
                proyeksi = harga

            harga_tampil = proyeksi if layer == "h7" else harga
            flat = fakta_service.flat_days(seri_penuh)
            try:
                umk = int(row["umk_2026_rp"])
            except (KeyError, ValueError):
                umk = None
            hasil_skor = skor_service.hitung(
                harga_rp=harga_tampil,
                acuan_rp=acuan,
                seri=seri_penuh,
                umk_rp=umk,
                komoditas=komoditas_kanonik,
                flat_days=flat,
            )
            selisih = hasil_skor["selisih_persen"]
            status = hasil_skor["status"]
            ews = hasil_skor["ews_score"]

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
                    sumber=asal,
                    jenis_harga=fakta_service.metode_data(asal),
                    flat_days=flat,
                    sifat_seri=fakta_service.sifat_seri(flat),
                    rekomendasi_tindakan=hasil_skor["rekomendasi_tindakan"],
                    risk_level=hasil_skor["risk_level"],
                )
            )

    cak = harga_service.cakupan()
    jumlah_berisi = sum(1 for i in items if i.harga_aktual_rp is not None)
    if jumlah_berisi:
        peringatan = []
    else:
        peringatan = ["SNAPSHOT_TIDAK_ADA"]
    if 0 < jumlah_berisi < 27:
        peringatan.append(f"CAKUPAN_SEBAGIAN_{jumlah_berisi}_DARI_27_WILAYAH")

    return EnvelopeResponse(
        data=items,
        meta=Meta(
            tanggal_data=tanggal_terbaru or (cak["periode"][1] if cak["periode"] else None),
            sumber=(
                ["Badan Pangan Nasional"] if sumber == "bapanas"
                else ["PIHPS BI", "SP2KP Kemendag"] if sumber == "utama"
                else ["SP2KP Kemendag"] if sumber == "sp2kp"
                else ["PIHPS BI"]
            ),
            mode_data="nyata" if cak["sumber"] else "demo",
            peringatan_kualitas=peringatan,
        ),
    )
