"""Uji layanan prediksi H+7 berbasis ANN Perceptron (5 -> 16 ReLU -> 1)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.services import bapanas as bapanas_service
from app.services import prediksi_ann as prediksi_ann_service

client = TestClient(app)


def test_seluruh_162_model_ann_terlatih():
    evaluasi = prediksi_ann_service.ringkasan_evaluasi()
    assert evaluasi["tersedia"] is True
    assert evaluasi["meta"]["metode"] == "ann_perceptron_5_16_1"
    assert evaluasi["meta"]["jumlah_model_terlatih"] == 162
    assert len(evaluasi["ringkasan_evaluasi_per_komoditas"]) == 6


def test_prediksi_ann_h7_per_wilayah_dan_komoditas():
    seri = bapanas_service.seri("Kab. Bekasi", "cabai_rawit_merah")
    assert len(seri) >= 22
    hasil = prediksi_ann_service.prediksi_h7("Kab. Bekasi", "cabai_rawit_merah", seri)
    assert hasil is not None
    assert hasil["metode"] == "ann_perceptron_5_16_1"
    assert hasil["horizon_hari"] == 7
    assert hasil["harga_prediksi_h7_rp"] > 0
    assert hasil["batas_bawah_h7_rp"] <= hasil["harga_prediksi_h7_rp"] <= hasil["batas_atas_h7_rp"]


def test_seri_terlalu_pendek_mengembalikan_none():
    assert prediksi_ann_service.prediksi_h7("Kab. Bekasi", "beras_medium", [("2026-10-31", 13500)]) is None


def test_endpoint_peta_layer_h7_dan_wilayah_ringkasan():
    res_peta = client.get("/api/v1/peta/status?komoditas=cabai_rawit_merah&layer=h7")
    assert res_peta.status_code == 200
    items = res_peta.json()["data"]
    assert len(items) == 27
    for item in items:
        assert item["harga_prediksi_h7_rp"] is not None and item["harga_prediksi_h7_rp"] > 0
        assert item["metode_prediksi"] == "ann_perceptron_5_16_1"

    res_wil = client.get("/api/v1/wilayah/32.16/ringkasan?komoditas=cabai_rawit_merah")
    assert res_wil.status_code == 200
    data_wil = res_wil.json()["data"]
    assert data_wil["harga_prediksi_h7_rp"] > 0
    assert data_wil["metode_prediksi"] == "ann_perceptron_5_16_1"


def test_endpoint_meta_evaluasi_ann():
    res = client.get("/api/v1/meta/evaluasi-ann")
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["tersedia"] is True
    assert "cabai_rawit_merah" in data["ringkasan_evaluasi_per_komoditas"]
