"""Skema Pydantic untuk kontrak REST API Radar Pangan.

Mendukung 100% kontrak data Front End (Dashboard & Landing Page)
dan kompatibel dua arah dengan spesifikasi backend resmi.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Dict, Generic, List, Literal, Optional, TypeVar
from pydantic import BaseModel, ConfigDict, Field, model_validator

T = TypeVar("T")

PriceStatus = Literal["aman", "waspada", "kritis", "turun", "tidak_ada_data"]
AcuanType = Literal["HET", "HAP", "DINAMIS_MEDIAN_90H"]
ModeData = Literal["nyata", "demo", "simulasi"]
LayerPeta = Literal["aktual", "h7"]


class Meta(BaseModel):
    """Metadata kejujuran data — wajib ada di setiap respons."""

    tanggal_data: Optional[str] = Field(
        "2026-10-23", description="Tanggal data harga (WIB). null bila tidak ada data."
    )
    diperbarui_pada: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Waktu respons dibuat (UTC, ISO-8601)",
    )
    sumber: List[str] = Field(
        default_factory=lambda: ["PIHPS BI", "Bapanas"],
        description='Mis. ["PIHPS BI", "Bapanas", "Laporan Warga"]',
    )
    is_simulasi: bool = Field(False, description="true bila hasil simulasi (bukan data nyata)")
    mode_data: ModeData = Field("demo", description="nyata | demo | simulasi")
    peringatan_kualitas: List[str] = Field(
        default_factory=list,
        description='Mis. ["HET_ILUSTRATIF", "DATA_HARI_SEBELUMNYA", "WILAYAH_TANPA_DATA"]',
    )


# Alias untuk ResponseMeta
ResponseMeta = Meta


class EnvelopeResponse(BaseModel, Generic[T]):
    """Amplop respons standar { ok, data, meta }."""

    ok: bool = True
    data: T
    meta: Meta = Field(default_factory=Meta)


# Alias Success untuk backward compatibility
Success = EnvelopeResponse


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
    detail: Optional[dict] = None
    coba_lagi_detik: Optional[int] = Field(None, description="Diisi saat HTTP 429")


class ErrorResponse(BaseModel):
    ok: Literal[False] = False
    error: ErrorBody


# ---------------------------------------------------------------- komoditas


class CommoditySchema(BaseModel):
    id: str = Field(description="ID kanonik komoditas, mis. beras_medium")
    name: str
    category: str = "Pangan Pokok"
    satuan: Literal["kg", "liter"]
    jenis_acuan: AcuanType
    harga_acuan_rp: int = Field(description="HET/HAP/median 90 hari (Rupiah)")
    deskripsi: str = ""

    # Aliases for compatibility
    kode: Optional[str] = None
    nama: Optional[str] = None
    keterangan_acuan: Optional[str] = None

    @model_validator(mode="after")
    def populate_aliases(self) -> CommoditySchema:
        if not self.kode:
            self.kode = self.id
        if not self.nama:
            self.nama = self.name
        if not self.keterangan_acuan:
            self.keterangan_acuan = self.deskripsi
        return self


Komoditas = CommoditySchema


# ------------------------------------------------------------------ wilayah


class RegionSchema(BaseModel):
    id: str = Field(description="Kode Kemendagri (PK, format NN.NN)", examples=["32.73"])
    code_bps: str = Field(description="Kode BPS 4 digit", examples=["3273"])
    name: str = Field(examples=["Kota Bandung"])
    type: Literal["KABUPATEN", "KOTA"]
    province_id: str = "32"
    province_name: str = "Jawa Barat"
    umk_2026_rp: int = Field(description="Upah Minimum Kabupaten/Kota 2026")
    garis_kemiskinan_rp: int = Field(description="Garis Kemiskinan Makanan per kapita")
    populasi: int = Field(description="Jumlah penduduk")
    lat: float
    lng: float

    # Aliases for compatibility
    kode_kemendagri: Optional[str] = None
    kode_bps: Optional[str] = None
    nama: Optional[str] = None
    jenis: Optional[Literal["kabupaten", "kota"]] = None
    provinsi: Optional[str] = None
    centroid: Optional[List[float]] = None
    status_geometri: Optional[Literal["lengkap", "hilang", "diganti_manual"]] = "lengkap"

    @model_validator(mode="after")
    def populate_aliases(self) -> RegionSchema:
        if not self.kode_kemendagri:
            self.kode_kemendagri = self.id
        if not self.kode_bps:
            self.kode_bps = self.code_bps
        if not self.nama:
            self.nama = self.name
        if not self.jenis:
            self.jenis = "kabupaten" if self.type == "KABUPATEN" else "kota"
        if not self.provinsi:
            self.provinsi = self.province_name
        if not self.centroid:
            self.centroid = [self.lat, self.lng]
        return self


Wilayah = RegionSchema


# --------------------------------------------------------------- peta status


class StatusPetaItem(BaseModel):
    region_id: str = Field(description="Kode Kemendagri NN.NN", examples=["32.73"])
    region_name: str = Field(examples=["Kota Bandung"])
    commodity_id: str = Field(examples=["cabai_rawit_merah"])
    harga_aktual_rp: Optional[int] = Field(None, description="null bila tidak ada data")
    harga_prediksi_h7_rp: Optional[int] = None
    harga_acuan_rp: int
    jenis_acuan: AcuanType
    selisih_persen: Optional[float] = Field(None, description="Gap terhadap acuan (%)")
    status: PriceStatus
    ews_score: Optional[int] = Field(None, ge=0, le=100, description="null bila tidak ada data")
    status_neraca: Optional[Literal["surplus", "seimbang", "defisit"]] = Field(
        None, description="null bila data neraca belum tersedia"
    )

    # Provenance per fakta (aditif)
    sumber: Optional[str] = Field(None, description="pihps | sp2kp")
    flat_days: Optional[int] = Field(
        None, description="Jumlah observasi terakhir dengan harga sama (0 = berubah terakhir)"
    )
    jenis_harga: Optional[Literal["resmi_bapanas"]] = Field(
        None,
        description="Fakta asal angka: dataset resmi Badan Pangan Nasional",
    )
    sifat_seri: Optional[Literal["bergerak", "statis"]] = Field(
        None, description="Turunan flat_days: statis bila >= 3 observasi terakhir sama"
    )
    rekomendasi_tindakan: Optional[str] = Field(
        None, description="Saran tindakan dari skor EWS (SSOT backend)"
    )
    risk_level: Optional[str] = Field(None, description="LOW | MEDIUM | HIGH | EXTREME")

    # Aliases for compatibility
    kode_kemendagri: Optional[str] = None
    nama: Optional[str] = None
    skor_ews: Optional[int] = None

    @model_validator(mode="after")
    def populate_aliases(self) -> StatusPetaItem:
        if not self.kode_kemendagri:
            self.kode_kemendagri = self.region_id
        if not self.nama:
            self.nama = self.region_name
        if self.skor_ews is None:
            self.skor_ews = self.ews_score
        return self


StatusWilayah = StatusPetaItem


class PetaStatusData(BaseModel):
    komoditas: str
    layer: LayerPeta
    jumlah_wilayah: int
    distribusi_status: Dict[str, int]
    wilayah: List[StatusPetaItem]


# ------------------------------------------------------------- detail wilayah


class TitikSeri(BaseModel):
    tanggal: str
    harga_rp: Optional[int]


class TitikPrakiraan(BaseModel):
    tanggal: str
    harga_rp: int
    batas_bawah_rp: int
    batas_atas_rp: int


class RegionDetailRingkasan(BaseModel):
    region: RegionSchema
    commodity: CommoditySchema
    harga_aktual_rp: Optional[int] = Field(None, description="null bila tidak ada data")
    harga_acuan_rp: int
    acuan_min_rp: Optional[int] = Field(None, description="Batas bawah HET/HAP bila ditetapkan sebagai rentang")
    acuan_max_rp: Optional[int] = Field(None, description="Batas atas HET/HAP")
    dasar_hukum: Optional[str] = Field(None, description="Regulasi penetapan acuan")
    harga_prediksi_h7_rp: Optional[int] = None
    selisih_persen: Optional[float] = None
    status: PriceStatus
    ews_score: Optional[int] = None
    risk_level: str = "LOW"
    rekomendasi_tindakan: Optional[str] = Field(
        None, description="Saran tindakan dari skor EWS (SSOT backend)"
    )
    history_14d: List[Dict[str, Any]] = Field(default_factory=list)
    supply_balance: Dict[str, Any]
    affordability: Dict[str, Any]

    # Aliases for compatibility with Abyan's structure
    seri_historis: Optional[List[TitikSeri]] = None
    prakiraan: Optional[List[TitikPrakiraan]] = None
    skor_ews: Optional[int] = None
    catatan_kondisi_khusus: Optional[str] = None

    @model_validator(mode="after")
    def populate_aliases(self) -> RegionDetailRingkasan:
        if self.skor_ews is None:
            self.skor_ews = self.ews_score
        if not self.seri_historis:
            self.seri_historis = [
                TitikSeri(tanggal=h.get("date", h.get("tanggal", "")), harga_rp=h.get("harga_rp"))
                for h in self.history_14d
            ]
        return self


DetailWilayahData = RegionDetailRingkasan


# ------------------------------------------------------------ ringkasan landing


class RingkasanLandingData(BaseModel):
    provinsi: str = "Jawa Barat"
    tanggal_data: Optional[str] = "2026-10-23"
    total_kabkota: int = 27
    kestabilan_wilayah_pct: float = 77.8
    jumlah_aman: int = 21
    jumlah_waspada: int = 4
    jumlah_kritis: int = 2
    komoditas_sorotan: Dict[str, Any]
    laporan_warga: Dict[str, Any]

    # Aliases for compatibility with Abyan's old structure
    judul: Optional[str] = "Radar Pangan — peringatan dini harga pangan Jawa Barat"
    jumlah_wilayah: Optional[int] = 27
    jumlah_komoditas: Optional[int] = 5
    distribusi_status: Optional[Dict[str, int]] = None
    sorotan: Optional[List[StatusPetaItem]] = None

    @model_validator(mode="after")
    def populate_aliases(self) -> RingkasanLandingData:
        if not self.distribusi_status:
            self.distribusi_status = {
                "aman": self.jumlah_aman,
                "waspada": self.jumlah_waspada,
                "kritis": self.jumlah_kritis,
                "turun": 0,
                "tidak_ada_data": 0,
            }
        return self


# ------------------------------------------------------- laporan warga


class LaporanRingkas(BaseModel):
    id: str
    region_id: str
    commodity_id: str
    harga_rp: int
    nama_pasar: str
    lat: float
    lng: float
    verified: bool = True
    status_konsensus: str
    created_at: str


class LaporanWargaInput(BaseModel):
    region_id: Optional[str] = "32.73"
    commodity_id: Optional[str] = "beras_medium"
    komoditas: Optional[str] = None  # alias
    harga_rp: int
    nama_pasar: Optional[str] = "Pasar Tradisional"
    lat: Optional[float] = None
    lng: Optional[float] = None
    latitude: Optional[float] = None  # alias
    longitude: Optional[float] = None  # alias
    satuan: Optional[Literal["kg", "liter"]] = "kg"
    catatan: Optional[str] = None

    @model_validator(mode="after")
    def normalize_fields(self) -> LaporanWargaInput:
        if self.komoditas and not self.commodity_id:
            self.commodity_id = self.komoditas
        if self.latitude is not None and self.lat is None:
            self.lat = self.latitude
        if self.longitude is not None and self.lng is None:
            self.lng = self.longitude
        if self.lat is None:
            self.lat = -6.9175
        if self.lng is None:
            self.lng = 107.6191
        return self


LaporanWargaCreate = LaporanWargaInput


class LaporanWargaCreated(BaseModel):
    id: str
    status: str = "DITERIMA"
    pesan: str
    status_klaster: Optional[str] = "sedang_berjalan"
    jumlah_laporan_klaster: Optional[int] = 1


# ------------------------------------------------------- AI Policy Advisor


