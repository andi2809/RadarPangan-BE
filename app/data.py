"""Data contoh (deterministik) untuk Radar Pangan.

PENTING: angka HET/HAP di sini ILUSTRATIF. Harga aktual beras memakai angka
nyata PIHPS (Jawa Barat, 23 Okt 2026 = Rp15.900/kg) sebagai jangkar demo.
Seluruh respons menandai meta.mode_data="demo" + peringatan "HET_ILUSTRATIF".
"""

from __future__ import annotations

import random
from datetime import date, datetime, timedelta, timezone

from .schemas import (
    DetailWilayahData,
    KlasterVerifikasi,
    Komoditas,
    LaporanRingkas,
    LaporanSekitarData,
    PetaStatusData,
    RingkasanLandingData,
    StatusWilayah,
    TitikPrakiraan,
    TitikSeri,
    Wilayah,
)

HARI_INI = date(2026, 10, 23)
WIB = timezone(timedelta(hours=7))

# (kode_kemendagri, kode_bps, nama, jenis, [lat, lng])
_WILAYAH_JABAR = [
    ("32.01", "3201", "Kab. Bogor", "kabupaten", [-6.4819, 106.8540]),
    ("32.02", "3202", "Kab. Sukabumi", "kabupaten", [-6.9277, 106.9300]),
    ("32.03", "3203", "Kab. Cianjur", "kabupaten", [-6.8170, 107.1420]),
    ("32.04", "3204", "Kab. Bandung", "kabupaten", [-7.0210, 107.5180]),
    ("32.05", "3205", "Kab. Garut", "kabupaten", [-7.2100, 107.9000]),
    ("32.06", "3206", "Kab. Tasikmalaya", "kabupaten", [-7.3500, 108.2200]),
    ("32.07", "3207", "Kab. Ciamis", "kabupaten", [-7.3300, 108.3500]),
    ("32.08", "3208", "Kab. Kuningan", "kabupaten", [-6.9760, 108.4840]),
    ("32.09", "3209", "Kab. Cirebon", "kabupaten", [-6.7500, 108.4800]),
    ("32.10", "3210", "Kab. Majalengka", "kabupaten", [-6.8360, 108.2270]),
    ("32.11", "3211", "Kab. Sumedang", "kabupaten", [-6.8580, 107.9200]),
    ("32.12", "3212", "Kab. Indramayu", "kabupaten", [-6.3260, 108.3200]),
    ("32.13", "3213", "Kab. Subang", "kabupaten", [-6.5710, 107.7580]),
    ("32.14", "3214", "Kab. Purwakarta", "kabupaten", [-6.5570, 107.4430]),
    ("32.15", "3215", "Kab. Karawang", "kabupaten", [-6.3010, 107.3060]),
    ("32.16", "3216", "Kab. Bekasi", "kabupaten", [-6.2600, 107.1500]),
    ("32.17", "3217", "Kab. Bandung Barat", "kabupaten", [-6.8300, 107.4800]),
    ("32.18", "3218", "Kab. Pangandaran", "kabupaten", [-7.6900, 108.4900]),
    ("32.71", "3271", "Kota Bogor", "kota", [-6.5950, 106.8160]),
    ("32.72", "3272", "Kota Sukabumi", "kota", [-6.9200, 106.9270]),
    ("32.73", "3273", "Kota Bandung", "kota", [-6.9175, 107.6191]),
    ("32.74", "3274", "Kota Cirebon", "kota", [-6.7320, 108.5520]),
    ("32.75", "3275", "Kota Bekasi", "kota", [-6.2647, 106.9899]),
    ("32.76", "3276", "Kota Depok", "kota", [-6.4025, 106.7942]),
    ("32.77", "3277", "Kota Cimahi", "kota", [-6.8730, 107.5425]),
    ("32.78", "3278", "Kota Tasikmalaya", "kota", [-7.3274, 108.2207]),
    ("32.79", "3279", "Kota Banjar", "kota", [-7.3667, 108.5333]),
]

WILAYAH: list[Wilayah] = [
    Wilayah(
        kode_kemendagri=k,
        kode_bps=b,
        nama=n,
        jenis=j,
        centroid=c,
        status_geometri="lengkap",
    )
    for k, b, n, j, c in _WILAYAH_JABAR
]

# harga_dasar = jangkar harga pasar demo (Rupiah per satuan)
KOMODITAS: list[Komoditas] = [
    Komoditas(
        kode="beras_medium",
        nama="Beras Medium",
        satuan="kg",
        jenis_acuan="HET",
        harga_acuan_rp=15500,
        keterangan_acuan="HET beras medium (ILUSTRATIF — ganti dengan Perbadan terbaru)",
    ),
    Komoditas(
        kode="cabai_rawit_merah",
        nama="Cabai Rawit Merah",
        satuan="kg",
        jenis_acuan="HAP",
        harga_acuan_rp=95000,
        keterangan_acuan="HAP konsumen Perbadan 12/2024 (ILUSTRATIF per zona)",
    ),
    Komoditas(
        kode="bawang_merah",
        nama="Bawang Merah",
        satuan="kg",
        jenis_acuan="HAP",
        harga_acuan_rp=42000,
        keterangan_acuan="HAP konsumen Perbadan 12/2024 (ILUSTRATIF per zona)",
    ),
    Komoditas(
        kode="telur_ayam_ras",
        nama="Telur Ayam Ras",
        satuan="kg",
        jenis_acuan="DINAMIS_MEDIAN_90H",
        harga_acuan_rp=28500,
        keterangan_acuan="Median nasional 90 hari — telur tidak punya HET",
    ),
    Komoditas(
        kode="minyak_goreng_curah",
        nama="Minyak Goreng Curah",
        satuan="kg",
        jenis_acuan="DINAMIS_MEDIAN_90H",
        harga_acuan_rp=18500,
        keterangan_acuan="Median 90 hari — PIHPS tidak memisahkan Minyakita; curah dipakai untuk MVP",
    ),
]

_HARGA_PASAR = {
    "beras_medium": 15900,  # angka nyata PIHPS Jabar 23/10/2026
    "cabai_rawit_merah": 102250,
    "bawang_merah": 41000,
    "telur_ayam_ras": 28400,
    "minyak_goreng_curah": 17400,
}

STATUS_ORDER = ["aman", "waspada", "kritis", "turun", "tidak_ada_data"]


def status_dari_selisih(selisih_persen: float | None) -> str:
    """Ambang yang dikunci Andi: ±5%, +5..10%, >+10%, <-5%."""
    if selisih_persen is None:
        return "tidak_ada_data"
    if selisih_persen > 10:
        return "kritis"
    if selisih_persen > 5:
        return "waspada"
    if selisih_persen < -5:
        return "turun"
    return "aman"


def _rng(kode: str, komoditas: str) -> random.Random:
    return random.Random(f"{kode}|{komoditas}")


def _harga_wilayah(kode: str, komoditas: str) -> int | None:
    """Harga per wilayah: ±6% deterministik dari harga pasar demo."""
    # Sengaja dikosongkan agar UI benar-benar menguji status "tidak_ada_data"
    # (kejujuran data: wilayah tanpa sumber tidak boleh diwarnai tebakan).
    if (kode, komoditas) in {("32.18", "beras_medium"), ("32.79", "cabai_rawit_merah")}:
        return None
    rng = _rng(kode, komoditas)
    if rng.random() < 0.04:  # ~4% wilayah lain juga tanpa data
        return None
    basis = _HARGA_PASAR[komoditas]
    return int(round(basis * (0.90 + rng.random() * 0.20)))


def _acuan(komoditas: str) -> Komoditas:
    return next(k for k in KOMODITAS if k.kode == komoditas)


def peta_status(komoditas: str, layer: str = "aktual") -> PetaStatusData:
    kom = _acuan(komoditas)
    hasil: list[StatusWilayah] = []
    distribusi = {s: 0 for s in STATUS_ORDER}

    for w in WILAYAH:
        harga = _harga_wilayah(w.kode_kemendagri, komoditas)
        # layer h7: proyeksi naik ~1,5% dari aktual
        prediksi = None if harga is None else int(round(harga * 1.015))
        dipakai = harga if layer == "aktual" or prediksi is None else prediksi
        selisih = (
            None if dipakai is None else round((dipakai - kom.harga_acuan_rp) / kom.harga_acuan_rp * 100, 2)
        )
        status = status_dari_selisih(selisih)
        distribusi[status] += 1
        rng = _rng(w.kode_kemendagri + layer, komoditas)
        hasil.append(
            StatusWilayah(
                kode_kemendagri=w.kode_kemendagri,
                nama=w.nama,
                status=status,
                jenis_acuan=kom.jenis_acuan,
                harga_aktual_rp=harga,
                harga_acuan_rp=kom.harga_acuan_rp,
                harga_prediksi_h7_rp=prediksi,
                selisih_persen=selisih,
                skor_ews=None if selisih is None else min(100, max(0, int(50 + selisih * 2 + rng.randint(-6, 6)))),
            )
        )

    return PetaStatusData(
        komoditas=komoditas,
        layer=layer,  # type: ignore[arg-type]
        jumlah_wilayah=len(hasil),
        distribusi_status=distribusi,
        wilayah=hasil,
    )


def detail_wilayah(kode: str, komoditas: str) -> DetailWilayahData | None:
    w = next((x for x in WILAYAH if x.kode_kemendagri == kode), None)
    if w is None:
        return None
    kom = _acuan(komoditas)
    rng = _rng(kode, komoditas)
    harga = _harga_wilayah(kode, komoditas)

    seri: list[TitikSeri] = []
    if harga is not None:
        for i in range(14, 0, -1):
            d = HARI_INI - timedelta(days=i - 1)
            if d.weekday() >= 5:  # Sabtu/Minggu: sumber resmi tidak terbit
                seri.append(TitikSeri(tanggal=d, harga_rp=None))
                continue
            nilai = int(round(harga * (0.97 + rng.random() * 0.05)))
            seri.append(TitikSeri(tanggal=d, harga_rp=nilai))

    prakiraan: list[TitikPrakiraan] = []
    if harga is not None:
        tren = 1.015 ** 0.5
        for h in range(1, 8):
            titik = harga * (tren ** h)
            pita = titik * 0.03 * h ** 0.5
            prakiraan.append(
                TitikPrakiraan(
                    tanggal=HARI_INI + timedelta(days=h),
                    harga_rp=int(round(titik)),
                    batas_bawah_rp=int(round(titik - pita)),
                    batas_atas_rp=int(round(titik + pita)),
                )
            )

    prediksi = prakiraan[-1].harga_rp if prakiraan else None
    selisih = None if harga is None else round((harga - kom.harga_acuan_rp) / kom.harga_acuan_rp * 100, 2)

    return DetailWilayahData(
        wilayah=w,
        komoditas=komoditas,
        status=status_dari_selisih(selisih),  # type: ignore[arg-type]
        jenis_acuan=kom.jenis_acuan,
        harga_acuan_rp=kom.harga_acuan_rp,
        harga_aktual_rp=harga,
        harga_prediksi_h7_rp=prediksi,
        selisih_persen=selisih,
        skor_ews=None if selisih is None else min(100, max(0, int(50 + selisih * 2))),
        seri_historis=seri,
        prakiraan=prakiraan,
        catatan_kondisi_khusus=None,
    )


def laporan_sekitar(lat: float, lng: float, komoditas: str) -> LaporanSekitarData:
    kom = _acuan(komoditas)
    rng = random.Random(f"laporan|{lat:.3f}|{lng:.3f}|{komoditas}")
    n = rng.randint(3, 9)
    laporan = [
        LaporanRingkas(
            komoditas=komoditas,
            harga_rp=int(round(_HARGA_PASAR[komoditas] * (0.97 + rng.random() * 0.06))),
            satuan=kom.satuan,
            jarak_m=rng.randint(120, 2800),
            dilaporkan_pada=datetime(2026, 10, 23, rng.randint(6, 11), rng.randint(0, 59), tzinfo=WIB),
            status_klaster="sedang_berjalan" if n < 10 else "terverifikasi",
        )
        for _ in range(n)
    ]
    return LaporanSekitarData(
        pusat_pencarian=[lat, lng],
        radius_m=3000,
        laporan=laporan,
        klaster=KlasterVerifikasi(
            pusat=[round(lat, 3), round(lng, 3)],
            radius_m=3000,
            jumlah_laporan=n,
            minimal_laporan=10,
            status="sedang_berjalan" if n < 10 else "terverifikasi",
            harga_konsensus_rp=None if n < 10 else laporan[0].harga_rp,
        ),
    )


def ringkasan_landing() -> RingkasanLandingData:
    peta = peta_status("beras_medium", "aktual")
    sorotan = sorted(
        [w for w in peta.wilayah if w.skor_ews is not None],
        key=lambda w: w.skor_ews or 0,
        reverse=True,
    )[:5]
    return RingkasanLandingData(
        judul="Radar Pangan — peringatan dini harga pangan Jawa Barat",
        jumlah_wilayah=len(WILAYAH),
        jumlah_komoditas=len(KOMODITAS),
        distribusi_status=peta.distribusi_status,
        sorotan=sorotan,
        tanggal_data=HARI_INI,
    )


def meta(sumber: list[str] | None = None) -> dict:
    return {
        "tanggal_data": HARI_INI,
        "diperbarui_pada": datetime.now(timezone.utc),
        "sumber": sumber or ["PIHPS BI"],
        "is_simulasi": False,
        "mode_data": "demo",
        "peringatan_kualitas": ["HET_ILUSTRATIF", "DATA_DEMO_BERLABEL"],
    }
