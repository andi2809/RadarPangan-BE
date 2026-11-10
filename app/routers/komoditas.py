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
        acuan_min_rp=13500,
        acuan_max_rp=13500,
        dasar_hukum="Perbadan Bapanas No. 5/2024 & Kepbadan No. 299/2025",
        deskripsi="Beras medium konsumen Wilayah 1 (Jawa, Lampung, Sumsel) HET Rp 13.500/kg (Premium Rp 14.900/kg)"
    ),
    CommoditySchema(
        id="cabai_rawit_merah",
        name="Cabai Rawit Merah",
        category="Hortikultura",
        satuan="kg",
        jenis_acuan="HAP",
        harga_acuan_rp=48500,
        acuan_min_rp=40000,
        acuan_max_rp=57000,
        harga_acuan_produsen_rp="Rp 25.000 - Rp 31.500/kg",
        dasar_hukum="Perbadan Bapanas No. 12/2024",
        deskripsi="Cabai rawit merah konsumen HAP Rp 40.000–57.000/kg (titik tengah acuan Rp 48.500/kg; produsen Rp 25.000–31.500/kg)"
    ),
    CommoditySchema(
        id="bawang_merah",
        name="Bawang Merah",
        category="Hortikultura",
        satuan="kg",
        jenis_acuan="HAP",
        harga_acuan_rp=39000,
        acuan_min_rp=36500,
        acuan_max_rp=41500,
        harga_acuan_produsen_rp="Konde Basah Rp 18.500–20.000/kg; Rogol Kering Panen Rp 25.000–30.000/kg; Konde Kering Askip Rp 32.000/kg",
        dasar_hukum="Perbadan Bapanas No. 12/2024",
        deskripsi="Bawang merah rogol kering panen konsumen HAP Rp 36.500–41.500/kg (titik tengah acuan Rp 39.000/kg; produsen Rp 25.000–30.000/kg)"
    ),
    CommoditySchema(
        id="telur_ayam_ras",
        name="Telur Ayam Ras",
        category="Peternakan",
        satuan="kg",
        jenis_acuan="HAP",
        harga_acuan_rp=30000,
        acuan_min_rp=30000,
        acuan_max_rp=30000,
        harga_acuan_produsen_rp="Rp 26.500/kg",
        dasar_hukum="Perbadan Bapanas No. 6/2024 & Kepbadan No. 529/2024",
        deskripsi="Telur ayam ras tingkat konsumen HAP Rp 30.000/kg (HAP pembelian di produsen Rp 26.500/kg)"
    ),
    CommoditySchema(
        id="minyak_goreng_curah",
        name="Minyak Goreng Curah",
        category="Minyak Nabati",
        satuan="liter",
        jenis_acuan="HET",
        harga_acuan_rp=15700,
        acuan_min_rp=15700,
        acuan_max_rp=15700,
        harga_acuan_produsen_rp="DPO Minyakita: Distributor Lini 1 Rp 13.500/L, Lini 2 Rp 14.000/L, Pengecer Rp 14.500/L",
        dasar_hukum="Kepmendag No. 1028/2024",
        deskripsi="Minyak goreng rakyat curah tingkat konsumen HET Rp 15.700/liter (DPO L1 Rp 13.500, L2 Rp 14.000, pengecer Rp 14.500)"
    ),
    CommoditySchema(
        id="minyak_goreng_kemasan",
        name="Minyak Goreng Kemasan",
        category="Minyak Nabati",
        satuan="liter",
        jenis_acuan="HET",
        harga_acuan_rp=15700,
        acuan_min_rp=15700,
        acuan_max_rp=15700,
        harga_acuan_produsen_rp="DPO Minyakita: Distributor Lini 1 Rp 13.500/L, Lini 2 Rp 14.000/L, Pengecer Rp 14.500/L",
        dasar_hukum="Kepmendag No. 1028/2024",
        deskripsi="Minyak goreng rakyat kemasan (Minyakita) tingkat konsumen HET Rp 15.700/liter (DPO L1 Rp 13.500, L2 Rp 14.000, pengecer Rp 14.500)"
    )
]

@router.get("", response_model=EnvelopeResponse[List[CommoditySchema]])
async def get_all_commodities():
    """Mengambil daftar 6 komoditas pangan pokok strategis beserta harga acuan resmi (HAP/HET)."""
    return EnvelopeResponse(data=COMMODITIES_DATA, meta=bapanas_service.meta_terkini())
