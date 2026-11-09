from fastapi import APIRouter

from app.routers.peta import get_peta_status
from app.schemas import EnvelopeResponse, Meta, RingkasanLandingData
from app.services import bapanas as bapanas_service

router = APIRouter(prefix="/api/v1/publik", tags=["Publik"])

NAMA_KOMODITAS = "Beras Medium"


def _ringkas_harga(items):
    """Rata-rata, titik terendah, dan titik tertinggi dari item yang punya harga."""
    berharga = [i for i in items if i.harga_aktual_rp]
    if not berharga:
        return None, None, None
    rata = round(sum(i.harga_aktual_rp for i in berharga) / len(berharga))
    return rata, min(berharga, key=lambda i: i.harga_aktual_rp), max(
        berharga, key=lambda i: i.harga_aktual_rp
    )


def _rupiah(nilai: int) -> str:
    return f"Rp {nilai:,.0f}".replace(",", ".")


@router.get("/ringkasan-landing", response_model=EnvelopeResponse[RingkasanLandingData])
async def get_ringkasan_landing():
    """Ringkasan landing dari snapshot PIHPS nyata (bukan angka demo).

    Bentuk respons dipertahankan agar kompatibel dengan front end; angka yang belum
    punya sumber (mis. laporan warga) dikembalikan 0 dan ditandai di meta.
    """
    # tanggal wajib eksplisit: default FastAPI adalah objek Query (truthy) saat dipanggil langsung.
    peta = await get_peta_status(komoditas="beras_medium", tanggal=None, layer="aktual")
    items = peta.data

    hitung = {"aman": 0, "waspada": 0, "kritis": 0, "turun": 0, "tidak_ada_data": 0}
    for item in items:
        hitung[item.status] = hitung.get(item.status, 0) + 1

    berdata = [i for i in items if i.status != "tidak_ada_data"]
    aman = hitung.get("aman", 0)
    kestabilan = round(100 * aman / len(berdata), 1) if berdata else 0.0

    rata, termurah, termahal = _ringkas_harga(items)
    status_jabar = max(
        (s for s in ("kritis", "waspada", "aman") if hitung.get(s)),
        key=lambda s: hitung[s],
        default="tidak_ada_data",
    )

    cak = bapanas_service.cakupan()
    peringatan = ["DATA_PIHPS_SNAPSHOT", "LAPORAN_WARGA_BELUM_TERSEDIA"]
    if cak["sumber"]:
        peringatan.append(f"CAKUPAN_SEBAGIAN_{cak['jumlah_wilayah']}_DARI_27_WILAYAH")
    else:
        peringatan.append("SNAPSHOT_PIHPS_TIDAK_ADA")

    ringkasan = RingkasanLandingData(
        provinsi="Jawa Barat",
        tanggal_data=peta.meta.tanggal_data,
        total_kabkota=len(items),
        kestabilan_wilayah_pct=kestabilan,
        jumlah_aman=aman,
        jumlah_waspada=hitung.get("waspada", 0),
        jumlah_kritis=hitung.get("kritis", 0),
        komoditas_sorotan={
            "nama": NAMA_KOMODITAS,
            "harga_rata_rata_rp": rata,
            "status_jabar": status_jabar,
            "sentra_surplus": f"{termurah.region_name} ({_rupiah(termurah.harga_aktual_rp)})" if termurah else None,
            "hotspot_kritis": f"{termahal.region_name} ({_rupiah(termahal.harga_aktual_rp)})" if termahal else None,
        },
        laporan_warga={"total_terverifikasi_hari_ini": 0, "akurasi_konsensus_pct": None},
        distribusi_status=hitung,
    )

    return EnvelopeResponse(
        data=ringkasan,
        meta=Meta(
            tanggal_data=peta.meta.tanggal_data,
            sumber=["PIHPS BI"],
            mode_data="nyata" if cak["sumber"] else "demo",
            peringatan_kualitas=peringatan,
        ),
    )
