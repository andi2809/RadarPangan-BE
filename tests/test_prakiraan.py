"""Uji prakiraan (SES + pita 95%) dan skor EWS sebagai SSOT."""

from __future__ import annotations

from app.services import prakiraan, skor


def _seri(nilai):
    return [(f"2026-10-{i+1:02d}", v) for i, v in enumerate(nilai)]


def test_titik_prediksi_selalu_harga_terakhir():
    for nilai in ([13500] * 10, [10000, 12000, 11000, 13000]):
        hasil = prakiraan.prakiraan_h7(_seri(nilai), komoditas="beras_medium", sumber="pihps")
        assert hasil["harga_prediksi_h7_rp"] == nilai[-1]
        assert hasil["metode"] == "naive"


def test_pita_empiris_dipakai_bila_tersedia():
    hasil = prakiraan.prakiraan_h7(_seri([15600] * 10), komoditas="beras_medium", sumber="pihps")
    assert hasil["metode_pita"] == "kuantil_empiris"
    assert hasil["batas_bawah_rp"] < 15600 < hasil["batas_atas_rp"]


def test_pita_fallback_sigma_saat_tanpa_komoditas():
    tenang = prakiraan.prakiraan_h7(_seri([10000, 10050, 10020, 10080] * 3))
    liar = prakiraan.prakiraan_h7(_seri([10000, 13000, 8000, 14000] * 3))
    assert tenang["metode_pita"] == "sigma"
    assert (liar["batas_atas_rp"] - liar["harga_prediksi_h7_rp"]) > (
        tenang["batas_atas_rp"] - tenang["harga_prediksi_h7_rp"]
    )


def test_data_terlalu_pendek_tidak_mengarang():
    assert prakiraan.prakiraan_h7(_seri([13500])) is None


def test_skor_konsisten_untuk_input_sama():
    a = skor.hitung(15600, 13500, _seri([15000, 15200, 15600]), 4_410_000, "beras_medium", 0)
    b = skor.hitung(15600, 13500, _seri([15000, 15200, 15600]), 4_410_000, "beras_medium", 0)
    assert a == b
    assert 0 <= a["ews_score"] <= 100
    assert a["status"] == "kritis"


def test_skor_harga_di_bawah_acuan_tidak_ekstrem():
    hasil = skor.hitung(30500, 32000, _seri([31000, 30800, 30500]), 4_410_000, "bawang_merah", 0)
    assert hasil["status"] == "aman"
    assert hasil["risk_level"] in ("LOW", "MEDIUM")
