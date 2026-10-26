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
