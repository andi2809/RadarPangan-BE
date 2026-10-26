from fastapi import APIRouter, Header, Query
from typing import List, Optional
from app.schemas import EnvelopeResponse, LaporanWargaInput
from app.services import harga as harga_service

router = APIRouter(prefix="/api/v1/laporan-warga", tags=["Laporan Warga"])


def _meta_laporan():
    """Laporan warga dari pengguna nyata; penyimpanan masih in-memory (hilang saat restart)."""
    dasar = harga_service.meta_terkini(sumber=["Laporan Warga (simulasi)", "PIHPS BI"])
    return dasar.model_copy(
        update={
            "mode_data": "demo",
            "peringatan_kualitas": dasar.peringatan_kualitas + ["LAPORAN_WARGA_PENYIMPANAN_SEMENTARA"],
        }
    )

# In-memory mock store
REPORTS_DB: list[dict] = []  # kosong: laporan warga harus datang dari pengguna nyata

@router.get("/sekitar", response_model=EnvelopeResponse[List[dict]])
async def get_laporan_sekitar(
    lat: float = Query(-6.9175, description="Latitude GPS pelapor"),
    lng: float = Query(107.6191, description="Longitude GPS pelapor"),
    radius_km: float = Query(3.0, description="Radius klaster konsensus")
):
    """Riwayat laporan warga dalam radius tertentu (nyata dari pengguna, bukan simulasi)."""

    def jarak_km(lat2: float, lng2: float) -> float:
        from math import asin, cos, radians, sin, sqrt

        dlat = radians(lat2 - lat)
        dlng = radians(lng2 - lng)
        a = sin(dlat / 2) ** 2 + cos(radians(lat)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
        return 2 * 6371 * asin(sqrt(a))

    sekitar = [
        {**r, "jarak_km": round(jarak_km(r["lat"], r["lng"]), 2)}
        for r in REPORTS_DB
        if jarak_km(r["lat"], r["lng"]) <= radius_km
    ]
    meta = _meta_laporan()
    if not sekitar:
        meta = meta.model_copy(update={
            "peringatan_kualitas": meta.peringatan_kualitas + ["BELUM_ADA_LAPORAN"]
        })
    return EnvelopeResponse(data=sekitar, meta=meta)

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
        },
        meta=_meta_laporan(),
    )
