"""Uji perilaku endpoint peta saat sumber fakta berbeda (PIHPS vs SP2KP)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

klien = TestClient(app)


def _peta(komoditas: str, sumber: str):
    r = klien.get(f"/api/v1/peta/status?komoditas={komoditas}&layer=aktual&sumber={sumber}")
    assert r.status_code == 200
    return r.json()["data"]


def test_pihps_tetap_jumlah_dan_label():
    data = _peta("beras_medium", "pihps")
    assert len(data) == 27
    berharga = [i for i in data if i["harga_aktual_rp"]]
    assert berharga, "PIHPS harus punya minimal satu wilayah berharga"
    assert all(i["sumber"] == "pihps" for i in data)
    assert all(i["jenis_harga"] == "pasar" for i in berharga)


def test_sp2kp_beras_lengkap_tapi_acuan():
    data = _peta("beras_medium", "sp2kp")
    berharga = [i for i in data if i["harga_aktual_rp"]]
    assert len(berharga) == 27, "SP2KP harus mencakup 27 wilayah untuk beras"
    assert all(i["jenis_harga"] == "acuan" for i in berharga)


@pytest.mark.parametrize("komoditas", ["cabai_rawit_merah", "bawang_merah"])
def test_sp2kp_komoditas_bergerak_ditandai_pasar(komoditas):
    data = _peta(komoditas, "sp2kp")
    berharga = [i for i in data if i["harga_aktual_rp"]]
    assert len(berharga) == 27
    assert all(i["jenis_harga"] == "pasar" for i in berharga)


def test_sp2kp_minyakita_ada_dan_acuan():
    data = _peta("minyakita", "sp2kp")
    berharga = [i for i in data if i["harga_aktual_rp"]]
    assert berharga, "SP2KP menyediakan Minyakita"
    assert all(i["jenis_harga"] == "acuan" for i in berharga)


def test_laporan_warga_kosong_dan_jujur():
    """Data laporan warga tidak boleh disimulasikan."""
    # koordinat jauh dari laporan mana pun -> harus kosong (tidak bergantung urutan tes)
    r = klien.get("/api/v1/laporan-warga/sekitar?lat=-8.5000&lng=112.0000&radius_km=3")
    assert r.status_code == 200
    body = r.json()
    assert body["data"] == [], "tidak boleh ada laporan karangan"
    peringatan = body["meta"]["peringatan_kualitas"]
    assert "BELUM_ADA_LAPORAN" in peringatan
    assert "LAPORAN_WARGA_SIMULASI" not in peringatan


def test_laporan_warga_masuk_setelah_dikirim():
    klien.post("/api/v1/laporan-warga", json={
        "region_id": "32.73", "commodity_id": "beras_medium", "harga_rp": 15000,
        "lat": -6.9175, "lng": 107.6191,
    })
    r = klien.get("/api/v1/laporan-warga/sekitar?lat=-6.9175&lng=107.6191&radius_km=3")
    assert len(r.json()["data"]) >= 1


def test_disparitas_tersedia():
    r = klien.get("/api/v1/meta/disparitas")
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["tersedia"] is True
    assert "pihps" in data and "sp2kp" in data
    assert data["sp2kp"]["komoditas"]["beras_medium"]["bergerak"] is False
    assert data["pihps"]["komoditas"]["beras_medium"]["bergerak"] is True


def test_flat_days_membedakan_komoditas_bergerak():
    """cabai bergerak harian; beras cenderung datar (indikator kualitas data)."""
    def median_flat(komoditas: str, sumber: str) -> int:
        data = _peta(komoditas, sumber)
        nilai = sorted(i["flat_days"] for i in data if i["harga_aktual_rp"])
        return nilai[len(nilai) // 2]

    assert median_flat("cabai_rawit_merah", "pihps") <= 2
    assert median_flat("beras_medium", "sp2kp") >= 4
    assert median_flat("beras_medium", "pihps") >= 10


def test_sumber_utama_menggabungkan_dengan_prioritas_pihps():
    data = _peta("beras_medium", "utama")
    berharga = [i for i in data if i["harga_aktual_rp"]]
    assert len(berharga) == 27
    sumber = {i["sumber"] for i in berharga}
    assert sumber == {"pihps", "sp2kp"}
    assert sum(1 for i in berharga if i["sumber"] == "pihps") == 9
    # beras dari SP2KP ditandai acuan, dari PIHPS pasar
    assert any(i["jenis_harga"] == "acuan" for i in berharga)
    assert any(i["jenis_harga"] == "pasar" for i in berharga)


def test_sumber_utama_cabai_semua_pasar():
    data = _peta("cabai_rawit_merah", "utama")
    berharga = [i for i in data if i["harga_aktual_rp"]]
    assert len(berharga) == 27
    assert all(i["jenis_harga"] == "pasar" for i in berharga)
