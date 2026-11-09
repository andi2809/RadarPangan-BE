"""Uji integritas data & determinisme — pengganti kontrak skema tanpa dependensi baru.

Yang dijaga:
- harga selalu bilangan positif
- kunci natural (tanggal, wilayah, komoditas) unik per snapshot dan setelah penggabungan
- tanggal tidak di masa depan
- wilayah/komoditas hanya yang dikenal
- pemuatan ulang deterministik (hasil sama persis)
- invarian endpoint peta (27 item, status sah, harga null <=> tidak_ada_data)
"""

from __future__ import annotations

import csv
import hashlib
from datetime import date
from pathlib import Path

import pytest

from app.services import bapanas as bapanas_service

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
REF = ROOT / "data" / "referensi" / "umk_jabar_2026.csv"
KOMODITAS = {"beras_medium", "cabai_rawit_merah", "bawang_merah", "telur_ayam_ras", "minyak_goreng_curah"}
STATUS_SAH = {"aman", "waspada", "kritis", "turun", "tidak_ada_data"}


def _semua_baris():
    for berkas in sorted(RAW.glob("bapanas_jabar_*.csv")):
        with berkas.open(encoding="utf-8") as fh:
            for baris in csv.DictReader(fh):
                baris["_berkas"] = berkas.name
                yield baris


def test_harga_positif_dan_angka():
    for baris in _semua_baris():
        nilai = (baris.get("harga_rp") or "").strip()
        if not nilai:
            continue
        assert nilai.isdigit(), f"harga bukan angka: {baris}"
        assert int(nilai) > 0, f"harga tidak positif: {baris}"


def test_kunci_unik_per_snapshot():
    for berkas in sorted(RAW.glob("bapanas_jabar_*.csv")):
        with berkas.open(encoding="utf-8") as fh:
            kunci = [(r["tanggal"], r["wilayah"], r["komoditas"]) for r in csv.DictReader(fh)]
        assert len(kunci) == len(set(kunci)), f"duplikat di {berkas.name}"


def test_gabungan_tidak_duplikat():
    for (wilayah, komoditas), seri in bapanas_service._muat()["harga"].items():
        tanggal = [t for t, _h in seri]
        assert len(tanggal) == len(set(tanggal)), f"tanggal ganda: {wilayah}/{komoditas}"
        assert tanggal == sorted(tanggal), f"seri tidak terurut: {wilayah}/{komoditas}"


def test_tanggal_tidak_di_masa_depan():
    batas = date.today().isoformat()
    for baris in _semua_baris():
        assert baris["tanggal"] <= batas, f"tanggal masa depan: {baris}"


def test_wilayah_dan_komoditas_dikenal():
    with REF.open(encoding="utf-8") as fh:
        wilayah_sah = {r["nama_wilayah"] for r in csv.DictReader(fh)}
    for baris in _semua_baris():
        assert baris["wilayah"] in wilayah_sah, f"wilayah asing: {baris['wilayah']}"
        assert baris["komoditas"] in KOMODITAS, f"komoditas asing: {baris['komoditas']}"


def test_pemuatan_ulang_deterministik():
    def sidik():
        muat = bapanas_service._muat()
        teks = repr(sorted((k, v) for k, v in muat["harga"].items()))
        return hashlib.sha256(teks.encode()).hexdigest()

    pertama = sidik()
    bapanas_service._muat.cache_clear()
    kedua = sidik()
    assert pertama == kedua, "hasil pemuatan berubah antar-run (tidak deterministik)"


@pytest.mark.parametrize("komoditas", sorted(KOMODITAS))
def test_invarian_peta(komoditas):
    from fastapi.testclient import TestClient
    from app.main import app

    data = TestClient(app).get(f"/api/v1/peta/status?komoditas={komoditas}&layer=aktual").json()["data"]
    assert len(data) == 27, f"{komoditas}: jumlah wilayah bukan 27"
    for item in data:
        assert item["status"] in STATUS_SAH, f"status tak dikenal: {item['status']}"
        if item["status"] == "tidak_ada_data":
            assert item["harga_aktual_rp"] is None
        else:
            assert item["harga_aktual_rp"] and item["harga_aktual_rp"] > 0
