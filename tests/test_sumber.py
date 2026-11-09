"""Uji sumber tunggal Bapanas dan perilaku endpoint peta/detail."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

klien = TestClient(app)


def _peta(komoditas: str, sumber: str = "bapanas"):
    r = klien.get(f"/api/v1/peta/status?komoditas={komoditas}&layer=aktual&sumber={sumber}")
    assert r.status_code == 200
    return r.json()["data"]


def test_bapanas_mencakup_27_wilayah():
    data = _peta("beras_medium")
    berharga = [i for i in data if i["harga_aktual_rp"]]
    assert len(berharga) == 27
    assert all(i["sumber"] == "bapanas" for i in berharga)


@pytest.mark.parametrize("komoditas", [
    "beras_medium", "cabai_rawit_merah", "bawang_merah",
    "telur_ayam_ras", "minyak_goreng_curah", "minyak_goreng_kemasan",
])
def test_enam_komoditas_tersedia(komoditas):
    data = _peta(komoditas)
    assert any(i["harga_aktual_rp"] for i in data), komoditas


def test_sumber_lain_ditolak():
    for sumber in ("pihps", "sp2kp", "utama"):
        r = klien.get(f"/api/v1/peta/status?komoditas=beras_medium&sumber={sumber}")
        assert r.status_code == 422, sumber


def test_flat_days_membedakan_komoditas_bergerak():
    def median_flat(komoditas: str) -> int:
        data = _peta(komoditas)
        nilai = sorted(i["flat_days"] for i in data if i["harga_aktual_rp"])
        return nilai[len(nilai) // 2]

    assert median_flat("cabai_rawit_merah") <= 3
    assert median_flat("beras_medium") >= 2


def test_skor_peta_dan_detail_konsisten():
    peta = _peta("beras_medium")
    item = next(i for i in peta if i["region_name"] == "Kota Bandung")
    detail = klien.get(
        "/api/v1/wilayah/32.73/ringkasan?komoditas=beras_medium&sumber=bapanas"
    ).json()["data"]
    assert item["ews_score"] == detail["ews_score"]
    assert item["status"] == detail["status"]
    assert item["risk_level"] == detail["risk_level"]
    assert detail["rekomendasi_tindakan"]


def test_acuan_memakai_rentang_regulasi():
    d = klien.get(
        "/api/v1/wilayah/32.73/ringkasan?komoditas=bawang_merah&sumber=bapanas"
    ).json()["data"]
    assert d["harga_acuan_rp"] == 39000
    assert d["acuan_min_rp"] == 36500
    assert d["acuan_max_rp"] == 41500
    assert "12/2024" in (d["dasar_hukum"] or "")
