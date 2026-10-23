"""Ekspor `openapi.json` + `fixtures/*.json` dari aplikasi FastAPI.

Cara pakai (dari root repo RadarPangan-Server):
    .venv/bin/python scripts/export_openapi.py
Hasil:
    openapi.json                      -> untuk Andi (sinkronisasi tipe) + lampiran proposal
    fixtures/*.json                   -> contoh respons untuk membangun FE tanpa backend
"""

from __future__ import annotations

import json
import pathlib
import sys

from fastapi.encoders import jsonable_encoder

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))  # agar `app` bisa diimpor saat dijalankan dari scripts/

from app import data  # noqa: E402
from app.main import app  # noqa: E402

FIXTURES = ROOT / "fixtures"


def _write(path: pathlib.Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    spec = app.openapi()
    _write(ROOT / "openapi.json", spec)

    contoh = {
        "ringkasan-landing.json": {
            "ok": True,
            "data": data.ringkasan_landing(),
            "meta": data.meta(),
        },
        "komoditas.json": {"ok": True, "data": data.KOMODITAS, "meta": data.meta()},
        "wilayah.json": {"ok": True, "data": data.WILAYAH, "meta": data.meta()},
        "peta-status-beras_medium-aktual.json": {
            "ok": True,
            "data": data.peta_status("beras_medium", "aktual"),
            "meta": data.meta(),
        },
        "wilayah-32.75-ringkasan-beras_medium.json": {
            "ok": True,
            "data": data.detail_wilayah("32.75", "beras_medium"),
            "meta": data.meta(),
        },
        "laporan-sekitar-32.75.json": {
            "ok": True,
            "data": data.laporan_sekitar(-6.2647, 106.9899, "beras_medium"),
            "meta": data.meta(["PIHPS BI", "Laporan Warga"]),
        },
    }
    for nama, payload in contoh.items():
        _write(FIXTURES / nama, jsonable_encoder(payload))

    print(f"openapi.json: {len(spec.get('paths', {}))} path")
    print(f"fixtures: {len(contoh)} file -> {FIXTURES}")


if __name__ == "__main__":
    main()
