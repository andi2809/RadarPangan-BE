from fastapi import APIRouter
from typing import List
from app.services import bapanas as bapanas_service
from app.schemas import EnvelopeResponse, CommoditySchema

router = APIRouter(prefix="/api/v1/komoditas", tags=["Komoditas"])

COMMODITIES_DATA: List[CommoditySchema] = [
    CommoditySchema(
        id="beras_medium",
        name="Beras Medium",
        category="Beras",
        satuan="kg",
        jenis_acuan="HET",
        harga_acuan_rp=13500,
        deskripsi="Beras butir patah maks 25%, acuan HET Zonasi I Jawa Barat (Perbadan 5/2024)"
    ),
    CommoditySchema(
        id="cabai_rawit_merah",
        name="Cabai Rawit Merah",
        category="Hortikultura",
        satuan="kg",
        jenis_acuan="HAP",
        harga_acuan_rp=45000,
        deskripsi="Cabai rawit merah segar tingkat konsumen, acuan HAP (Perbadan 12/2024)"
    ),
    CommoditySchema(
        id="bawang_merah",
        name="Bawang Merah",
        category="Hortikultura",
        satuan="kg",
        jenis_acuan="HAP",
        harga_acuan_rp=32000,
        deskripsi="Bawang merah rogol kering panen, acuan HAP konsumen (Perbadan 12/2024)"
    ),
    CommoditySchema(
        id="telur_ayam_ras",
        name="Telur Ayam Ras",
        category="Peternakan",
        satuan="kg",
        jenis_acuan="DINAMIS_MEDIAN_90H",
        harga_acuan_rp=29500,
        deskripsi="Telur ayam ras segar, acuan dinamis moving-median 90 hari kalender"
    ),
    CommoditySchema(
        id="minyak_goreng_curah",
        name="Minyak Goreng Curah",
        category="Minyak Nabati",
        satuan="liter",
        jenis_acuan="HET",
        harga_acuan_rp=15700,
        deskripsi="Minyak goreng curah rakyat, acuan HET (Permendag 18/2024)"
    ),
    CommoditySchema(
        id="minyak_goreng_kemasan",
        name="Minyak Goreng Kemasan",
        category="Minyak Nabati",
        satuan="liter",
        jenis_acuan="DINAMIS_MEDIAN_90H",
        harga_acuan_rp=19700,
        deskripsi="Minyak goreng kemasan; acuan mengikuti median 90 hari karena tidak diatur HET"
    )
]

@router.get("", response_model=EnvelopeResponse[List[CommoditySchema]])
async def get_all_commodities():
    """Mengambil daftar 6 komoditas pangan pokok strategis beserta harga acuan resmi (HAP/HET)."""
    return EnvelopeResponse(data=COMMODITIES_DATA, meta=bapanas_service.meta_terkini())
