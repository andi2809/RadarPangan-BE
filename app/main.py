"""Radar Pangan — FastAPI (MVP 1 Nov 2026).

Jalankan:
    uvicorn app.main:app --reload --port 8000
Swagger UI:  http://localhost:8000/docs
OpenAPI:     http://localhost:8000/openapi.json

Catatan: seluruh data di sini DEMO BERLABEL (meta.mode_data="demo") dan
angka HET/HAP masih ILUSTRATIF — wajib diganti dengan nilai resmi sebelum final.
"""

from __future__ import annotations

from datetime import date

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware

from . import data
from .schemas import (
    DetailWilayahData,
    ErrorResponse,
    Komoditas,
    LaporanSekitarData,
    LaporanWargaCreate,
    LaporanWargaCreated,
    LayerPeta,
    PetaStatusData,
    RingkasanLandingData,
    Success,
    Wilayah,
)

TAGS = {
    "publik": "Data publik (tanpa auth)",
    "peta": "Peta status harga",
    "wilayah": "Detail wilayah",
    "laporan": "Laporan warga (verifikasi)",
    "sistem": "Kesehatan layanan",
}

app = FastAPI(
    title="Radar Pangan API",
    version="0.1.0",
    description=(
        "API MVP Radar Pangan — GIS early warning + decision support harga pangan "
        "Jawa Barat (27 kab/kota, 5 komoditas).\n\n"
        "**Kejujuran data:** setiap respons membawa `meta.tanggal_data`, "
        "`meta.mode_data` (nyata/demo) dan `meta.peringatan_kualitas`. "
        "Wilayah tanpa data dikembalikan dengan `status=tidak_ada_data` — tidak ditebak."
    ),
    openapi_tags=[{"name": v, "description": v} for v in TAGS.values()],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # MVP: longgarkan agar Netlify/Vercel bisa akses
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


async def api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> str:
    """MVP: API key sederhana (keputusan Andi: JWT menyusul di fase penyisihan)."""
    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail={"ok": False, "error": {"kode": "TIDAK_TEROTENTIKASI", "pesan": "Header X-API-Key wajib diisi."}},
        )
    return x_api_key


def _cek_komoditas(kode: str) -> str:
    if kode not in {k.kode for k in data.KOMODITAS}:
        raise HTTPException(
            status_code=404,
            detail={"ok": False, "error": {"kode": "DATA_TIDAK_DITEMUKAN", "pesan": f"Komoditas '{kode}' tidak dikenal."}},
        )
    return kode


# ------------------------------------------------------------------ sistem


@app.get("/api/health", tags=[TAGS["sistem"]], summary="Health check")
def health() -> dict:
    return {
        "ok": True,
        "data": {
            "status": "sehat",
            "versi": app.version,
            "mode_data": "demo",
            "tanggal_data": data.HARI_INI.isoformat(),
        },
        "meta": data.meta(),
    }


# ------------------------------------------------------------------ publik


@app.get(
    "/api/v1/publik/ringkasan-landing",
    tags=[TAGS["publik"]],
    response_model=Success[RingkasanLandingData],
    summary="Ringkasan untuk landing page",
    responses={
        200: {
            "description": "Agregat status + 5 wilayah sorotan",
            "content": {"application/json": {"example": jsonable_encoder({
                "ok": True,
                "data": data.ringkasan_landing(),
                "meta": data.meta(),
            })}},
        }
    },
)
def ringkasan_landing():
    return {"ok": True, "data": data.ringkasan_landing(), "meta": data.meta()}


@app.get(
    "/api/v1/komoditas",
    tags=[TAGS["publik"]],
    response_model=Success[list[Komoditas]],
    summary="Daftar 5 komoditas kanonik + acuan",
    responses={
        200: {
            "content": {"application/json": {"example": jsonable_encoder({
                "ok": True,
                "data": data.KOMODITAS,
                "meta": data.meta(),
            })}}
        }
    },
)
def komoditas():
    return {"ok": True, "data": data.KOMODITAS, "meta": data.meta()}


@app.get(
    "/api/v1/wilayah",
    tags=[TAGS["publik"]],
    response_model=Success[list[Wilayah]],
    summary="Daftar kabupaten/kota Jawa Barat",
    responses={
        200: {
            "content": {"application/json": {"example": jsonable_encoder({
                "ok": True,
                "data": data.WILAYAH[:3],
                "meta": data.meta(),
            })}}
        }
    },
)
def wilayah(q: str | None = Query(None, description="Cari nama, mis. 'bekasi'")):
    hasil = data.WILAYAH
    if q:
        hasil = [w for w in hasil if q.lower() in w.nama.lower()]
    return {"ok": True, "data": hasil, "meta": data.meta()}


# --------------------------------------------------------------------- peta


@app.get(
    "/api/v1/peta/status",
    tags=[TAGS["peta"]],
    response_model=Success[PetaStatusData],
    summary="Choropleth status harga (aktual atau H+7)",
    responses={
        200: {
            "content": {"application/json": {"example": jsonable_encoder({
                "ok": True,
                "data": data.peta_status("beras_medium", "aktual"),
                "meta": data.meta(),
            })}}
        }
    },
)
def peta_status(
    komoditas: str = Query("beras_medium", examples=["beras_medium"]),
    tanggal: date | None = Query(None, description="Default: tanggal data terakhir"),
    layer: LayerPeta = Query("aktual", description="aktual | h7"),
):
    _cek_komoditas(komoditas)
    return {
        "ok": True,
        "data": data.peta_status(komoditas, layer),
        "meta": data.meta(),
    }


# ------------------------------------------------------------------ wilayah


@app.get(
    "/api/v1/wilayah/{kode}/ringkasan",
    tags=[TAGS["wilayah"]],
    response_model=Success[DetailWilayahData],
    summary="Detail satu wilayah: seri 14 hari + prakiraan H+7",
    responses={
        200: {
            "content": {"application/json": {"example": jsonable_encoder({
                "ok": True,
                "data": data.detail_wilayah("32.75", "beras_medium"),
                "meta": data.meta(),
            })}}
        },
        404: {"model": ErrorResponse, "description": "Wilayah tidak ditemukan"},
    },
)
def detail_wilayah(kode: str, komoditas: str = Query("beras_medium")):
    _cek_komoditas(komoditas)
    hasil = data.detail_wilayah(kode, komoditas)
    if hasil is None:
        raise HTTPException(
            status_code=404,
            detail={"ok": False, "error": {"kode": "DATA_TIDAK_DITEMUKAN", "pesan": f"Wilayah '{kode}' tidak ada."}},
        )
    return {"ok": True, "data": hasil, "meta": data.meta()}


# ------------------------------------------------------------------ laporan


@app.get(
    "/api/v1/laporan-warga/sekitar",
    tags=[TAGS["laporan"]],
    response_model=Success[LaporanSekitarData],
    summary="Harga sekitar + progres klaster verifikasi (n dari 10)",
    responses={
        200: {
            "content": {"application/json": {"example": jsonable_encoder({
                "ok": True,
                "data": data.laporan_sekitar(-6.2647, 106.9899, "beras_medium"),
                "meta": data.meta(["PIHPS BI", "Laporan Warga"]),
            })}}
        }
    },
)
def laporan_sekitar(
    lat: float = Query(..., ge=-11.1, le=6.2, examples=[-6.2647]),
    lng: float = Query(..., ge=94.9, le=141.1, examples=[106.9899]),
    komoditas: str = Query("beras_medium"),
):
    _cek_komoditas(komoditas)
    return {
        "ok": True,
        "data": data.laporan_sekitar(lat, lng, komoditas),
        "meta": data.meta(["PIHPS BI", "Laporan Warga"]),
    }


@app.post(
    "/api/v1/laporan-warga",
    tags=[TAGS["laporan"]],
    response_model=Success[LaporanWargaCreated],
    status_code=201,
    summary="Kirim laporan harga warga (wajib X-API-Key)",
    responses={
        201: {
            "content": {"application/json": {"example": jsonable_encoder({
                "ok": True,
                "data": LaporanWargaCreated(
                    id="lpr_20261023_0001",
                    status_klaster="sedang_berjalan",
                    jumlah_laporan_klaster=7,
                ),
                "meta": data.meta(["Laporan Warga"]),
            })}}
        },
        401: {"model": ErrorResponse, "description": "API key tidak ada"},
    },
)
def kirim_laporan(payload: LaporanWargaCreate, _kunci: str = Depends(api_key)):
    _cek_komoditas(payload.komoditas)
    return {
        "ok": True,
        "data": LaporanWargaCreated(
            id="lpr_20261023_0001",
            status_klaster="sedang_berjalan",
            jumlah_laporan_klaster=7,
        ),
        "meta": data.meta(["Laporan Warga"]),
    }
