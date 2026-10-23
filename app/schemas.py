"""Skema Pydantic untuk kontrak REST API Radar Pangan (MVP 1 Nov).

Semua respons memakai amplop seragam: {ok, data, meta}.
Field mengikuti keputusan Andi (23 Okt 2026): jenis_acuan, harga_acuan_rp,
harga_aktual_rp, harga_prediksi_h7_rp, selisih_persen, status.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")

StatusHarga = Literal["aman", "waspada", "kritis", "turun", "tidak_ada_data"]
JenisAcuan = Literal["HET", "HAP", "DINAMIS_MEDIAN_90H"]
LayerPeta = Literal["aktual", "h7"]
ModeData = Literal["nyata", "demo"]


class Meta(BaseModel):
    """Metadata kejujuran data — wajib ada di setiap respons."""

    tanggal_data: date | None = Field(
        None, description="Tanggal data harga (WIB). null bila tidak ada data."
    )
    diperbarui_pada: datetime = Field(description="Waktu respons dibuat (UTC, ISO-8601)")
    sumber: list[str] = Field(
        default_factory=list, description='Mis. ["PIHPS BI", "Laporan Warga"]'
    )
    is_simulasi: bool = Field(False, description="true bila hasil simulasi (bukan data nyata)")
    mode_data: ModeData = Field("demo", description="nyata | demo (seed berlabel)")
    peringatan_kualitas: list[str] = Field(
        default_factory=list,
        description='Mis. ["HET_ILUSTRATIF", "DATA_HARI_SEBELUMNYA", "WILAYAH_TANPA_DATA"]',
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "tanggal_data": "2026-10-23",
                "diperbarui_pada": "2026-10-23T07:15:00Z",
                "sumber": ["PIHPS BI", "Laporan Warga"],
                "is_simulasi": False,
                "mode_data": "demo",
                "peringatan_kualitas": ["HET_ILUSTRATIF"],
            }
        }
    )


class Success(BaseModel, Generic[T]):
    """Amplop respons sukses."""

    ok: Literal[True] = True
    data: T
    meta: Meta


class ErrorBody(BaseModel):
    kode: Literal[
        "VALIDASI_GAGAL",
        "TIDAK_TEROTENTIKASI",
        "AKSES_DITOLAK",
        "WILAYAH_DI_LUAR_YURISDIKSI",
        "DATA_TIDAK_DITEMUKAN",
        "BATAS_LAJU_TERLAMPAUI",
        "HARGA_DI_LUAR_RENTANG_WAJAR",
        "KOORDINAT_DI_LUAR_INDONESIA",
        "GALAT_INTERNAL",
    ]
    pesan: str = Field(description="Bahasa Indonesia, netral, tidak menyalahkan warga")
    detail: dict | None = None
    coba_lagi_detik: int | None = Field(None, description="Diisi saat HTTP 429")


class ErrorResponse(BaseModel):
    ok: Literal[False] = False
    error: ErrorBody


# ---------------------------------------------------------------- komoditas


class Komoditas(BaseModel):
    kode: str = Field(description="Kode kanonik, mis. beras_medium")
    nama: str
    satuan: Literal["kg", "liter"]
    jenis_acuan: JenisAcuan
    harga_acuan_rp: int = Field(description="HET/HAP/median 90 hari (Rupiah)")
    keterangan_acuan: str = Field(description="Dasar hukum atau metode acuan")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "kode": "beras_medium",
                "nama": "Beras Medium",
                "satuan": "kg",
                "jenis_acuan": "HET",
                "harga_acuan_rp": 12500,
                "keterangan_acuan": "HET beras medium zona Jawa (ILUSTRATIF — ganti dengan Perbadan terbaru)",
            }
        }
    )


# ------------------------------------------------------------------ wilayah


class Wilayah(BaseModel):
    kode_kemendagri: str = Field(description="PK, format NN.NN", examples=["32.75"])
    kode_bps: str = Field(description="Kode BPS 4 digit", examples=["3275"])
    nama: str = Field(examples=["Kota Bekasi"])
    jenis: Literal["kabupaten", "kota"]
    provinsi: str = "Jawa Barat"
    centroid: list[float] = Field(description="[lat, lng] pusat pemerintahan")
    status_geometri: Literal["lengkap", "hilang", "diganti_manual"] = "lengkap"

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "kode_kemendagri": "32.75",
                "kode_bps": "3275",
                "nama": "Kota Bekasi",
                "jenis": "kota",
                "provinsi": "Jawa Barat",
                "centroid": [-6.2647, 106.9899],
                "status_geometri": "lengkap",
            }
        }
    )


# --------------------------------------------------------------- peta status


class StatusWilayah(BaseModel):
    kode_kemendagri: str
    nama: str
    status: StatusHarga
    jenis_acuan: JenisAcuan | None = None
    harga_aktual_rp: int | None = Field(None, description="null bila tidak ada data")
    harga_acuan_rp: int | None = None
    harga_prediksi_h7_rp: int | None = None
    selisih_persen: float | None = Field(None, description="Gap terhadap acuan (%)")
    skor_ews: int | None = Field(None, ge=0, le=100)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "kode_kemendagri": "32.75",
                "nama": "Kota Bekasi",
                "status": "kritis",
                "jenis_acuan": "HET",
                "harga_aktual_rp": 15900,
                "harga_acuan_rp": 12500,
                "harga_prediksi_h7_rp": 16350,
                "selisih_persen": 27.2,
                "skor_ews": 78,
            }
        }
    )


class PetaStatusData(BaseModel):
    komoditas: str
    layer: LayerPeta
    jumlah_wilayah: int
    distribusi_status: dict[str, int] = Field(
        description="Jumlah wilayah per status",
        json_schema_extra={"example": {"aman": 0, "waspada": 0, "kritis": 0, "turun": 0, "tidak_ada_data": 0}},
    )
    wilayah: list[StatusWilayah]


# ------------------------------------------------------------- detail wilayah


class TitikSeri(BaseModel):
    tanggal: date
    harga_rp: int | None


class TitikPrakiraan(BaseModel):
    tanggal: date
    harga_rp: int
    batas_bawah_rp: int
    batas_atas_rp: int


class DetailWilayahData(BaseModel):
    wilayah: Wilayah
    komoditas: str
    status: StatusHarga
    jenis_acuan: JenisAcuan
    harga_acuan_rp: int
    harga_aktual_rp: int | None
    harga_prediksi_h7_rp: int | None
    selisih_persen: float | None
    skor_ews: int | None = Field(None, ge=0, le=100)
    seri_historis: list[TitikSeri] = Field(description="H-14 s/d hari ini (data nyata)")
    prakiraan: list[TitikPrakiraan] = Field(description="H+1 s/d H+7 (model regresi)")
    catatan_kondisi_khusus: str | None = Field(
        None, description="Mis. jumlah peserta didik dengan alergi/fobia/intoleran (bila ada)"
    )


# ------------------------------------------------------- laporan warga (S3)


class LaporanRingkas(BaseModel):
    komoditas: str
    harga_rp: int
    satuan: Literal["kg", "liter"]
    jarak_m: int
    dilaporkan_pada: datetime
    status_klaster: Literal["belum_terverifikasi", "sedang_berjalan", "terverifikasi"]


class KlasterVerifikasi(BaseModel):
    pusat: list[float] = Field(description="[lat, lng] pusat klaster (grid 0,001°)")
    radius_m: int = 3000
    jumlah_laporan: int
    minimal_laporan: int = 10
    status: Literal["belum_terverifikasi", "sedang_berjalan", "terverifikasi"]
    harga_konsensus_rp: int | None = None


class LaporanSekitarData(BaseModel):
    pusat_pencarian: list[float]
    radius_m: int
    laporan: list[LaporanRingkas]
    klaster: KlasterVerifikasi


class LaporanWargaCreate(BaseModel):
    komoditas: str = Field(examples=["beras_medium"])
    harga_rp: int = Field(gt=0, le=5_000_000, examples=[15900])
    satuan: Literal["kg", "liter"] = "kg"
    latitude: float = Field(ge=-11.1, le=6.2, examples=[-6.2647])
    longitude: float = Field(ge=94.9, le=141.1, examples=[106.9899])
    catatan: str | None = Field(None, max_length=280)


class LaporanWargaCreated(BaseModel):
    id: str = Field(examples=["lpr_20261023_0001"])
    status_klaster: Literal["belum_terverifikasi", "sedang_berjalan", "terverifikasi"]
    jumlah_laporan_klaster: int = Field(examples=[7])
    minimal_laporan: int = 10


# ------------------------------------------------------------ ringkasan landing


class RingkasanLandingData(BaseModel):
    judul: str
    jumlah_wilayah: int
    jumlah_komoditas: int
    distribusi_status: dict[str, int]
    sorotan: list[StatusWilayah] = Field(description="5 wilayah dengan skor EWS tertinggi")
    tanggal_data: date | None
