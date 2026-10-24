from fastapi import APIRouter
from app.schemas import EnvelopeResponse, RingkasanLandingData

router = APIRouter(prefix="/api/v1/publik", tags=["Publik"])

@router.get("/ringkasan-landing", response_model=EnvelopeResponse[RingkasanLandingData])
async def get_ringkasan_landing():
    """Mengembalikan data ringkas statistik dan stabilitas pangan Jawa Barat untuk Landing Page."""
    summary = RingkasanLandingData(
        provinsi="Jawa Barat",
        tanggal_data="2026-10-23",
        total_kabkota=27,
        kestabilan_wilayah_pct=77.8,
        jumlah_aman=21,
        jumlah_waspada=4,
        jumlah_kritis=2,
        komoditas_sorotan={
            "nama": "Cabai Rawit Merah",
            "harga_rata_rata_rp": 64200,
            "status_jabar": "waspada",
            "sentra_surplus": "Kab. Garut (Rp 54.000)",
            "hotspot_kritis": "Kab. Pangandaran (Rp 78.000)"
        },
        laporan_warga={
            "total_terverifikasi_hari_ini": 84,
            "akurasi_konsensus_pct": 94.2
        }
    )
    return EnvelopeResponse(data=summary)
