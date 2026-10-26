import csv
import json
from datetime import date, timedelta
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from app.schemas import EnvelopeResponse, RegionSchema, RegionDetailRingkasan, CommoditySchema, TitikPrakiraan
from app.routers.komoditas import COMMODITIES_DATA
from app.services import harga as harga_service

router = APIRouter(prefix="/api/v1/wilayah", tags=["Wilayah"])

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
REF_DIR = DATA_DIR / "referensi"
GEO_DIR = DATA_DIR / "geo"

def _normalize_commodity_code(code: str) -> str:
    if code == "minyak_goreng_curah":
        return "minyakita"
    return code

def _load_regions_from_csv() -> List[RegionSchema]:
    csv_path = REF_DIR / "umk_jabar_2026.csv"
    centroids_path = GEO_DIR / "jabar-centroids.json"
    centroids = {}
    if centroids_path.exists():
        with open(centroids_path, "r", encoding="utf-8") as f:
            centroids = json.load(f)

    regions = []
    if csv_path.exists():
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                kid = row["kode_kemendagri"]
                c = centroids.get(kid, {"lat": -6.9175, "lng": 107.6191})
                regions.append(
                    RegionSchema(
                        id=kid,
                        code_bps=row["kode_bps"],
                        name=row["nama_wilayah"],
                        type=row["tipe"],
                        province_id="32",
                        province_name="Jawa Barat",
                        umk_2026_rp=int(row["umk_2026_rp"]),
                        garis_kemiskinan_rp=int(row["garis_kemiskinan_rp"]),
                        populasi=int(row["populasi"]),
                        lat=c.get("lat", -6.9175),
                        lng=c.get("lng", 107.6191)
                    )
                )
    return regions

@router.get("", response_model=EnvelopeResponse[List[RegionSchema]])
async def list_wilayah(q: Optional[str] = Query(None, description="Cari nama wilayah, mis. 'Bandung'")):
    """Mengambil daftar 27 Kabupaten/Kota Jawa Barat lengkap dengan kode Kemendagri, UMK 2026, dan centroid."""
    regions = _load_regions_from_csv()
    if q:
        regions = [r for r in regions if q.lower() in r.name.lower()]
    return EnvelopeResponse(data=regions, meta=harga_service.meta_terkini())

@router.get("/{kode}/ringkasan", response_model=EnvelopeResponse[RegionDetailRingkasan])
async def get_wilayah_ringkasan(kode: str, komoditas: str = Query("beras_medium", description="ID komoditas")):
    """Mengambil ringkasan telemetri satu wilayah: harga aktual, HET/HAP, H+7, EWS score, tren, dan daya beli UMK."""
    regions = _load_regions_from_csv()
    target_reg = next((r for r in regions if r.id == kode), None)
    if not target_reg:
        raise HTTPException(status_code=404, detail=f"Wilayah dengan kode {kode} tidak ditemukan")

    clean_komoditas = _normalize_commodity_code(komoditas)

    # Acuan mapping
    acuan_map = {
        "beras_medium": (13500, "HET"),
        "cabai_rawit_merah": (45000, "HAP"),
        "bawang_merah": (32000, "HAP"),
        "telur_ayam_ras": (29500, "DINAMIS_MEDIAN_90H"),
        "minyakita": (15700, "HET")
    }
    harga_acuan, jenis = acuan_map.get(clean_komoditas, (13500, "HET"))

    # Harga nyata dari snapshot PIHPS; wilayah tanpa data tidak dikarang.
    titik = harga_service.terakhir(target_reg.name, clean_komoditas)
    seri = harga_service.seri(target_reg.name, clean_komoditas, limit=14)

    if titik is None:
        harga_aktual = None
        selisih_persen = None
        harga_prediksi_h7 = None
        status = "tidak_ada_data"
        ews_score = None
        risk_level = "TIDAK_DIKETAHUI"
        base_date = date.today()
        history: list[dict] = []
        prakiraan: list[TitikPrakiraan] = []
    else:
        tanggal_data, harga_aktual = titik
        base_date = date.fromisoformat(tanggal_data)
        nilai = [v for _t, v in seri]
        if len(nilai) >= 2 and nilai[0] > 0:
            laju = (nilai[-1] - nilai[0]) / max(1, len(nilai) - 1) / nilai[0]
        else:
            laju = 0.0
        harga_prediksi_h7 = round(harga_aktual * (1 + laju * 7))
        selisih_persen = round((harga_aktual - harga_acuan) / harga_acuan * 100, 2)

        status = "aman"
        if selisih_persen > 10:
            status = "kritis"
        elif selisih_persen > 5:
            status = "waspada"
        elif selisih_persen < -5:
            status = "turun"

        ews_score = min(100, max(0, int(50 + selisih_persen * 2)))
        risk_level = "TINGGI" if ews_score > 65 else ("SEDANG" if ews_score > 45 else "RENDAH")

        history = [{"date": t, "tanggal": t, "harga_rp": v} for t, v in seri]

        prakiraan = []
        for h in range(1, 8):
            d = base_date + timedelta(days=h)
            val = round(harga_aktual * (1 + laju * h))
            margin = round(val * 0.02 * (h ** 0.5))
            prakiraan.append(
                TitikPrakiraan(
                    tanggal=d.isoformat(),
                    harga_rp=val,
                    batas_bawah_rp=val - margin,
                    batas_atas_rp=val + margin,
                )
            )

    comm_found = next((c for c in COMMODITIES_DATA if c.id == clean_komoditas), None)
    if not comm_found:
        comm_found = CommoditySchema(
            id=clean_komoditas,
            name=clean_komoditas.replace("_", " ").title(),
            category="Pangan Pokok",
            satuan="kg",
            jenis_acuan=jenis,
            harga_acuan_rp=harga_acuan,
            deskripsi=f"Acuan resmi {jenis}"
        )

    data = RegionDetailRingkasan(
        region=target_reg,
        commodity=comm_found,
        harga_aktual_rp=harga_aktual,
        harga_acuan_rp=harga_acuan,
        harga_prediksi_h7_rp=harga_prediksi_h7,
        selisih_persen=selisih_persen,
        status=status,
        ews_score=ews_score,
        risk_level=risk_level,
        history_14d=history,
        prakiraan=prakiraan,
        supply_balance={
            # Data neraca pasokan belum tersedia -> jangan mengarang angka.
            "status_neraca": None,
            "keterangan": "Data neraca pasokan belum tersedia",
        },
        affordability={
            "umk_ratio_basket_pct": round((950000 / target_reg.umk_2026_rp) * 100, 1),
            "kategori": "RENTAN" if (harga_aktual or 0) > harga_acuan else "TERJANGKAU"
        }
    )

    return EnvelopeResponse(data=data, meta=harga_service.meta_terkini())
