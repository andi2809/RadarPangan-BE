import csv
import json
from pathlib import Path
from typing import List, Optional, Literal
from fastapi import APIRouter, Query
from app.schemas import EnvelopeResponse, StatusPetaItem, PriceStatus, AcuanType

router = APIRouter(prefix="/api/v1/peta", tags=["Peta"])

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
REF_DIR = DATA_DIR / "referensi"

def _normalize_commodity_code(code: str) -> str:
    if code == "minyak_goreng_curah":
        return "minyakita"
    return code

@router.get("/status", response_model=EnvelopeResponse[List[StatusPetaItem]])
async def get_peta_status(
    komoditas: str = Query("beras_medium", description="ID komoditas kanonik"),
    tanggal: Optional[str] = Query(None, description="Tanggal observasi YYYY-MM-DD"),
    layer: Literal["aktual", "h7"] = Query("aktual", description="Lapisan visualisasi data (aktual | h7)")
):
    """Mengembalikan array status harga dan EWS untuk 27 Kabupaten/Kota Jawa Barat
    yang langsung dikonsumsi layer choropleth pada front end."""
    csv_path = REF_DIR / "umk_jabar_2026.csv"
    items: List[StatusPetaItem] = []

    clean_komoditas = _normalize_commodity_code(komoditas)

    # Acuan defaults
    acuan_map = {
        "beras_medium": (13500, "HET"),
        "cabai_rawit_merah": (45000, "HAP"),
        "bawang_merah": (32000, "HAP"),
        "telur_ayam_ras": (29500, "DINAMIS_MEDIAN_90H"),
        "minyakita": (15700, "HET")
    }
    harga_acuan, jenis_acuan = acuan_map.get(clean_komoditas, (13500, "HET"))

    if csv_path.exists():
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                kid = row["kode_kemendagri"]
                kname = row["nama_wilayah"]

                # Dynamic variation factors
                factor = 1.01
                if clean_komoditas == "cabai_rawit_merah":
                    if kid in ["32.73", "32.75", "32.76", "32.01"]:
                        factor = 1.15 if layer == "aktual" else 1.21  # Kritis
                    elif kid in ["32.05", "32.03"]:
                        factor = 0.97  # Aman/Surplus
                elif clean_komoditas == "beras_medium":
                    if kid in ["32.12", "32.15", "32.13"]:
                        factor = 0.94  # Surplus Indramayu/Karawang
                    elif kid in ["32.73", "32.75"]:
                        factor = 1.07  # Waspada

                h0 = round((harga_acuan * factor) / 100) * 100
                h7 = round((h0 * (1.04 if factor > 1.05 else 1.01)) / 100) * 100

                active_price = h7 if layer == "h7" else h0
                selisih_pct = round(((active_price - harga_acuan) / harga_acuan) * 100, 2)

                status: PriceStatus = "aman"
                if selisih_pct > 10:
                    status = "kritis"
                elif selisih_pct > 5:
                    status = "waspada"
                elif selisih_pct < -5:
                    status = "turun"

                ews_score = min(100, max(15, round((selisih_pct + 5) * 5)))

                neraca: Literal["surplus", "seimbang", "defisit"] = "seimbang"
                if factor < 0.96:
                    neraca = "surplus"
                elif factor > 1.09:
                    neraca = "defisit"

                items.append(
                    StatusPetaItem(
                        region_id=kid,
                        region_name=kname,
                        commodity_id=clean_komoditas,
                        harga_aktual_rp=h0,
                        harga_prediksi_h7_rp=h7,
                        harga_acuan_rp=harga_acuan,
                        jenis_acuan=jenis_acuan,
                        selisih_persen=selisih_pct,
                        status=status,
                        ews_score=ews_score,
                        status_neraca=neraca
                    )
                )

    return EnvelopeResponse(data=items)
