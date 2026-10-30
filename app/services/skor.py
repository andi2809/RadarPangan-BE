"""Skor EWS tunggal (SSOT) — dipakai peta maupun detail wilayah.

Formula: 45% deviasi terhadap acuan + 35% laju tren + 20% daya beli UMK.
Alasan ditulis di `docs/KESIMPULAN_METODOLOGI.md`; uji backtest di `data/derived/backtest_*.json`.

Penjaga penting: bila seri harga statis (`flat_days >= 3`), tren dianggap nol —
tanpa ini, seri datar bisa menghasilkan skor tren yang menyesatkan.
"""

from __future__ import annotations

from typing import Iterable, Optional

BOBOT_DEVIASI = 0.45
BOBOT_TREN = 0.35
BOBOT_DAYA_BELI = 0.20

LAJU_NORMAL_RP_PER_HARI = {
    "cabai_rawit_merah": 300.0,
    "beras_medium": 50.0,
}
LAJU_NORMAL_DEFAULT = 150.0

BERAT_BULANAN_KG = {"beras_medium": 10.0}
BERAT_BULANAN_DEFAULT = 2.0

AMBANG_STATIS = 3


def _clamp(nilai: float, bawah: float = 0.0, atas: float = 100.0) -> float:
    return max(bawah, min(atas, nilai))


def status_dari_selisih(selisih: Optional[float]) -> str:
    """Ambang terkunci: aman ±5%, waspada >5–10%, kritis >10%, turun < −5%."""
    if selisih is None:
        return "tidak_ada_data"
    if selisih > 10:
        return "kritis"
    if selisih > 5:
        return "waspada"
    if selisih < -5:
        return "turun"
    return "aman"


def laju_harian(seri: Iterable[tuple[str, int]], flat_days: int) -> float:
    """Kemiringan rupiah/hari; nol bila seri statis atau titik kurang."""
    titik = list(seri)
    if len(titik) < 2 or flat_days >= AMBANG_STATIS:
        return 0.0
    return (titik[-1][1] - titik[0][1]) / max(1, len(titik) - 1)


def hitung(
    harga_rp: int,
    acuan_rp: int,
    seri: Iterable[tuple[str, int]],
    umk_rp: Optional[int],
    komoditas: str,
    flat_days: int,
) -> dict:
    """Hitung skor EWS + status + tingkat risiko + rekomendasi tindakan."""
    selisih = (harga_rp - acuan_rp) / acuan_rp * 100 if acuan_rp else None
    deviasi = _clamp((selisih + 5) * 4) if selisih is not None else 0.0

    laju = laju_harian(seri, flat_days)
    normal = LAJU_NORMAL_RP_PER_HARI.get(komoditas, LAJU_NORMAL_DEFAULT)
    tren = _clamp((laju / normal) * 50 + 30)

    if umk_rp:
        berat = BERAT_BULANAN_KG.get(komoditas, BERAT_BULANAN_DEFAULT)
        daya_beli = _clamp((harga_rp * berat) / (umk_rp * 0.10) * 100)
    else:
        daya_beli = 50.0

    skor = round(deviasi * BOBOT_DEVIASI + tren * BOBOT_TREN + daya_beli * BOBOT_DAYA_BELI)
    skor = int(_clamp(skor))
    status = status_dari_selisih(selisih)

    if skor >= 75 or status == "kritis":
        risiko = "EXTREME"
        rekomendasi = (
            "Operasi Pasar Murah (GPM) darurat dan aktivasi Fasilitasi Distribusi Pangan (FDP) "
            "dari sentra surplus terdekat."
        )
    elif skor >= 55:
        risiko = "HIGH"
        rekomendasi = (
            "Peringatan dini lonjakan harga. Koordinasikan pelepasan Cadangan Pangan Pemerintah "
            "Daerah (CPPD)."
        )
    elif skor >= 35:
        risiko = "MEDIUM"
        rekomendasi = "Pantau harian dan verifikasi stok di pasar utama."
    else:
        risiko = "LOW"
        rekomendasi = "Pasokan stabil. Pertahankan pemantauan rutin."

    return {
        "selisih_persen": round(selisih, 2) if selisih is not None else None,
        "status": status,
        "ews_score": skor,
        "risk_level": risiko,
        "rekomendasi_tindakan": rekomendasi,
        "komponen": {
            "deviasi": round(deviasi, 1),
            "tren": round(tren, 1),
            "daya_beli": round(daya_beli, 1),
            "laju_rp_per_hari": round(laju, 1),
        },
    }
