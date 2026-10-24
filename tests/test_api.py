import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_get_komoditas():
    response = client.get("/api/v1/komoditas")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert len(body["data"]) == 5
    ids = [c["id"] for c in body["data"]]
    assert "beras_medium" in ids
    assert "cabai_rawit_merah" in ids
    assert "bawang_merah" in ids
    assert "telur_ayam_ras" in ids
    assert "minyakita" in ids

def test_get_wilayah():
    response = client.get("/api/v1/wilayah")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert len(body["data"]) == 27  # 27 Kab/Kota Jawa Barat
    # Verify Kemendagri format
    assert body["data"][0]["id"].startswith("32.")
    assert "umk_2026_rp" in body["data"][0]

def test_get_peta_status():
    response = client.get("/api/v1/peta/status?komoditas=cabai_rawit_merah&layer=aktual")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert len(body["data"]) == 27
    item = body["data"][0]
    assert "region_id" in item
    assert "status" in item
    assert "selisih_persen" in item
    statuses = {i["status"] for i in body["data"]}
    assert any(s in ["aman", "waspada", "kritis", "turun"] for s in statuses)

def test_get_wilayah_ringkasan():
    response = client.get("/api/v1/wilayah/32.73/ringkasan?komoditas=beras_medium")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    data = body["data"]
    assert data["region"]["id"] == "32.73"
    assert "history_14d" in data
    assert len(data["history_14d"]) >= 14
    assert "supply_balance" in data
    assert "affordability" in data
    assert "prakiraan" in data

def test_laporan_warga_anonymous():
    response = client.post("/api/v1/laporan-warga", json={
        "region_id": "32.73",
        "commodity_id": "beras_medium",
        "harga_rp": 14500,
        "nama_pasar": "Pasar Caringin",
        "lat": -6.9421,
        "lng": 107.5758
    })
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["data"]["status"] == "DITERIMA"

def test_ai_briefing():
    response = client.post("/api/v1/ai/briefing", json={
        "region_id": "32.73",
        "commodity_id": "cabai_rawit_merah"
    })
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert "executive_briefing_markdown" in body["data"]
    assert "TPID JAWA BARAT" in body["data"]["executive_briefing_markdown"]
