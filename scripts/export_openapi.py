"""Ekspor `openapi.json` + `fixtures/*.json` dari aplikasi FastAPI.

Cara pakai (dari root repo RadarPangan-Server):
    PYTHONPATH=. python3 scripts/export_openapi.py
Hasil:
    openapi.json    -> skema OpenAPI v3
    fixtures/*.json -> contoh respons nyata untuk mock front end
"""

from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.main import app
from fastapi.testclient import TestClient

FIXTURES = ROOT / "fixtures"


def _write(path: pathlib.Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    client = TestClient(app)

    # 1. Export OpenAPI spec
    spec = app.openapi()
    _write(ROOT / "openapi.json", spec)

    # 2. Export Real HTTP Responses via TestClient
    endpoints = {
        "ringkasan-landing.json": "/api/v1/publik/ringkasan-landing",
        "komoditas.json": "/api/v1/komoditas",
        "wilayah.json": "/api/v1/wilayah",
        "peta-status-beras_medium-aktual.json": "/api/v1/peta/status?komoditas=beras_medium&layer=aktual",
        "wilayah-32.75-ringkasan-beras_medium.json": "/api/v1/wilayah/32.75/ringkasan?komoditas=beras_medium",
        "laporan-sekitar-32.75.json": "/api/v1/laporan-warga/sekitar?lat=-6.2647&lng=106.9899",
    }

    for filename, path in endpoints.items():
        resp = client.get(path)
        if resp.status_code == 200:
            _write(FIXTURES / filename, resp.json())
        else:
            print(f"Warning: Failed to fetch {path}: status {resp.status_code}")

    print(f"openapi.json: {len(spec.get('paths', {}))} paths exported")
    print(f"fixtures: {len(endpoints)} files exported -> {FIXTURES}")


if __name__ == "__main__":
    main()
