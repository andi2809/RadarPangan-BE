import csv
import json
from datetime import date, timedelta
from pathlib import Path
from typing import List, Literal, Optional
from fastapi import APIRouter, HTTPException, Query
from app.schemas import EnvelopeResponse, RegionSchema, RegionDetailRingkasan, CommoditySchema, TitikPrakiraan
from app.routers.komoditas import COMMODITIES_DATA
from app.services import acuan as acuan_service
from app.services import bapanas as bapanas_service
from app.services import indikator as indikator_service
from app.services import bapanas as bapanas_service
from app.services import prakiraan as prakiraan_service
from app.services import skor as skor_service

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
    return EnvelopeResponse(data=regions, meta=bapanas_service.meta_terkini())

@router.get("/{kode}/ringkasan", response_model=EnvelopeResponse[RegionDetailRingkasan])
async def get_wilayah_ringkasan(
    kode: str,
    komoditas: str = Query("beras_medium", description="ID komoditas"),
    sumber: Literal["bapanas"] = Query(
        "bapanas", description="Sumber tunggal: dataset resmi Badan Pangan Nasional"
    ),
):
    """Mengambil ringkasan telemetri satu wilayah: harga aktual, HET/HAP, H+7, EWS score, tren, dan daya beli UMK."""
    regions = _load_regions_from_csv()
    target_reg = next((r for r in regions if r.id == kode), None)
    if not target_reg:
        raise HTTPException(status_code=404, detail=f"Wilayah dengan kode {kode} tidak ditemukan")

    clean_komoditas = _normalize_commodity_code(komoditas)

    data_acuan = acuan_service.untuk(clean_komoditas)
    harga_acuan = data_acuan["acuan_rp"] if data_acuan else 13500
    jenis = data_acuan["jenis"] if data_acuan else "HET"

    # Harga nyata dari snapshot terpilih; wilayah tanpa data tidak dikarang.
    titik = bapanas_service.terakhir(target_reg.name, clean_komoditas)
    asal = "bapanas"
    seri_penuh = bapanas_service.seri(target_reg.name, clean_komoditas)
    seri = seri_penuh[-14:] if seri_penuh else []

    if titik is None:
        harga_aktual = None
        selisih_persen = None
        harga_prediksi_h7 = None
        status = "tidak_ada_data"
        ews_score = None
        risk_level = "TIDAK_DIKETAHUI"
        rekomendasi_tindakan = None
        base_date = date.today()
        history: list[dict] = []
        prakiraan: list[TitikPrakiraan] = []
    else:
        tanggal_data, harga_aktual = titik
        base_date = date.fromisoformat(tanggal_data)
        nilai = [v for _t, v in seri]
        prog = prakiraan_service.prakiraan_h7(
            seri, indikator_service.flat_days(seri), komoditas=clean_komoditas, sumber=asal
        )
        harga_prediksi_h7 = prog["harga_prediksi_h7_rp"] if prog else harga_aktual

        hasil_skor = skor_service.hitung(
            harga_rp=harga_aktual,
            acuan_rp=harga_acuan,
            seri=seri_penuh,
            umk_rp=target_reg.umk_2026_rp,
            komoditas=clean_komoditas,
            flat_days=indikator_service.flat_days(seri_penuh),
        )
        selisih_persen = hasil_skor["selisih_persen"]
        status = hasil_skor["status"]
        ews_score = hasil_skor["ews_score"]
        risk_level = hasil_skor["risk_level"]
        rekomendasi_tindakan = hasil_skor["rekomendasi_tindakan"]

        history = [{"date": t, "tanggal": t, "harga_rp": v} for t, v in seri]

        prakiraan = []
        lebar_pita = (
            (prog["batas_atas_rp"] - prog["harga_prediksi_h7_rp"]) / prog["harga_prediksi_h7_rp"]
            if prog and prog["harga_prediksi_h7_rp"] else 0.02
        )
        for h in range(1, 8):
            d = base_date + timedelta(days=h)
            val = round(harga_aktual + (harga_prediksi_h7 - harga_aktual) * h / 7)
            margin = round(val * lebar_pita * (h / 7) ** 0.5)
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
        acuan_min_rp=data_acuan["min_rp"] if data_acuan else None,
        acuan_max_rp=data_acuan["max_rp"] if data_acuan else None,
        dasar_hukum=data_acuan["dasar_hukum"] if data_acuan else None,
            deskripsi=f"Acuan resmi {jenis}"
        )

    data = RegionDetailRingkasan(
        region=target_reg,
        commodity=comm_found,
        harga_aktual_rp=harga_aktual,
        harga_acuan_rp=harga_acuan,
        acuan_min_rp=data_acuan["min_rp"] if data_acuan else None,
        acuan_max_rp=data_acuan["max_rp"] if data_acuan else None,
        dasar_hukum=data_acuan["dasar_hukum"] if data_acuan else None,
        harga_prediksi_h7_rp=harga_prediksi_h7,
        selisih_persen=selisih_persen,
        status=status,
        ews_score=ews_score,
        risk_level=risk_level,
        rekomendasi_tindakan=rekomendasi_tindakan,
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

    return EnvelopeResponse(data=data, meta=bapanas_service.meta_terkini())
