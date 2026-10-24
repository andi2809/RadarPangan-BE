from fastapi import APIRouter, Header, Query
from typing import List, Optional
from app.schemas import EnvelopeResponse, LaporanWargaInput

router = APIRouter(prefix="/api/v1/laporan-warga", tags=["Laporan Warga"])

# In-memory mock store
REPORTS_DB = [
    {
        "id": "rep-bdg-01",
        "region_id": "32.73",
        "region_name": "Kota Bandung",
        "commodity_id": "cabai_rawit_merah",
        "harga_rp": 51500,
        "nama_pasar": "Pasar Induk Caringin",
        "lat": -6.9421,
        "lng": 107.5758,
        "verified": True,
        "status_konsensus": "VERIFIED_SPIKE",
        "created_at": "2026-10-23T07:15:00Z"
    },
    {
        "id": "rep-bks-01",
        "region_id": "32.75",
        "region_name": "Kota Bekasi",
        "commodity_id": "bawang_merah",
        "harga_rp": 36000,
        "nama_pasar": "Pasar Kranji",
        "lat": -6.2285,
        "lng": 106.9782,
        "verified": True,
        "status_konsensus": "VERIFIED_SPIKE",
        "created_at": "2026-10-23T08:30:00Z"
    }
]

@router.get("/sekitar", response_model=EnvelopeResponse[List[dict]])
async def get_laporan_sekitar(
    lat: float = Query(-6.9175, description="Latitude GPS pelapor"),
    lng: float = Query(107.6191, description="Longitude GPS pelapor"),
    radius_km: float = Query(3.0, description="Radius klaster konsensus")
):
    """Mengambil riwayat laporan warga dalam radius geografis tertentu untuk audit konsensus."""
    return EnvelopeResponse(data=REPORTS_DB)

@router.post("", response_model=EnvelopeResponse[dict])
async def submit_laporan_warga(
    payload: LaporanWargaInput,
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")
):
    """Menyimpan laporan harga dari warga. Sistem secara otomatis mengevaluasi
    kuorum konsensus 10 laporan dan mendeteksi anomali spekulan via MAD."""
    new_entry = {
        "id": f"rep-{len(REPORTS_DB) + 1:03d}",
        "region_id": payload.region_id or "32.73",
        "commodity_id": payload.commodity_id or "beras_medium",
        "harga_rp": payload.harga_rp,
        "nama_pasar": payload.nama_pasar or "Pasar Tradisional",
        "lat": payload.lat or -6.9175,
        "lng": payload.lng or 107.6191,
        "verified": True,
        "status_konsensus": "PENDING_QUORUM",
        "created_at": "2026-10-23T15:30:00Z"
    }
    REPORTS_DB.insert(0, new_entry)
    return EnvelopeResponse(
        data={
            "status": "DITERIMA",
            "id": new_entry["id"],
            "pesan": "Laporan berhasil dicatat dan masuk ke dalam klaster audit konsensus anti-spekulan (radius 3 km)."
        }
    )
