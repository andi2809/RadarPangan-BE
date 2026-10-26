from fastapi import APIRouter
from typing import List
from app.services import harga as harga_service
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
        id="minyakita",
        name="Minyakita",
        category="Minyak Nabati",
        satuan="liter",
        jenis_acuan="HET",
        harga_acuan_rp=15700,
        deskripsi="Minyak goreng kemasan bantal/botol rakyat, acuan HET (Permendag 18/2024)"
    )
]

@router.get("", response_model=EnvelopeResponse[List[CommoditySchema]])
async def get_all_commodities():
    """Mengambil daftar 5 komoditas pangan pokok strategis beserta harga acuan resmi (HAP/HET)."""
    return EnvelopeResponse(data=COMMODITIES_DATA, meta=harga_service.meta_terkini())
