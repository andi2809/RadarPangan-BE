"""Metadata sumber data: registry + jejak jalur distribusi (lineage).

GET /api/v1/meta/sumber        -> daftar sumber, tier, cakupan, kesegaran
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter

from app.schemas import EnvelopeResponse
from app.services import harga as harga_service

router = APIRouter(prefix="/api/v1/meta", tags=["Metadata"])

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "data" / "registry.json"
RUNLOG = ROOT / "data" / "derived" / "runs.jsonl"
DERIVED = ROOT / "data" / "derived"

SEGAR_JAM = 36


def _baca_json(path: Path, bawaan):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return bawaan


def _run_terakhir() -> Dict[str, Dict[str, Any]]:
    hasil: Dict[str, Dict[str, Any]] = {}
    if not RUNLOG.is_file():
        return hasil
    with RUNLOG.open(encoding="utf-8") as fh:
        for baris in fh:
            baris = baris.strip()
            if not baris:
                continue
            try:
                catatan = json.loads(baris)
            except json.JSONDecodeError:
                continue
            sumber = catatan.get("sumber")
            if sumber:
                hasil[sumber] = catatan
    return hasil


def _umur_jam(iso: str | None) -> float | None:
    if not iso:
        return None
    try:
        waktu = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return None
    if waktu.tzinfo is None:
        waktu = waktu.replace(tzinfo=timezone.utc)
    return round((datetime.now(timezone.utc) - waktu).total_seconds() / 3600, 1)


@router.get("/sumber", response_model=EnvelopeResponse[Dict[str, Any]])
async def get_sumber():
    """Registry sumber + run terakhir + status kesegaran."""
    registry = _baca_json(REGISTRY, {"sumber": []})
    terakhir = _run_terakhir()

    baris: List[Dict[str, Any]] = []
    for item in registry.get("sumber", []):
        jalan = terakhir.get(item["id"])
        umur = _umur_jam(jalan.get("selesai")) if jalan else None
        baris.append(
            {
                **item,
                "run_terakhir": jalan,
                "umur_jam": umur,
                "segar": (umur is not None and umur <= SEGAR_JAM),
            }
        )

    return EnvelopeResponse(
        data={
            "diperbarui": registry.get("diperbarui"),
            "ambang_segar_jam": SEGAR_JAM,
            "sumber": baris,
        },
        meta=harga_service.meta_terkini(),
    )


@router.get("/disparitas", response_model=EnvelopeResponse[Dict[str, Any]])
async def get_disparitas():
    """Sebaran harga antarwilayah per hari — sinyal alternatif saat level harga datar."""
    berkas = DERIVED / "disparitas.json"
    if not berkas.is_file():
        return EnvelopeResponse(
            data={"tersedia": False, "catatan": "belum ada hasil disparitas"},
            meta=harga_service.meta_terkini(),
        )
    return EnvelopeResponse(
        data={"tersedia": True, "berkas": berkas.name, **_baca_json(berkas, {})},
        meta=harga_service.meta_terkini(),
    )


@router.get("/backtest", response_model=EnvelopeResponse[Dict[str, Any]])
async def get_backtest():
    """Hasil backtest EWS terbaru (kinerja ambang, bukan klaim akurasi)."""
    berkas = sorted(DERIVED.glob("backtest_*.json"))
    if not berkas:
        return EnvelopeResponse(
            data={"tersedia": False, "catatan": "belum ada hasil backtest"},
            meta=harga_service.meta_terkini(),
        )
    isi = _baca_json(berkas[-1], {})
    return EnvelopeResponse(
        data={"tersedia": True, "berkas": berkas[-1].name, **isi},
        meta=harga_service.meta_terkini(),
    )


@router.get("/integritas", response_model=EnvelopeResponse[Dict[str, Any]])
async def get_integritas():
    """Hasil pemeriksaan integritas paket Bapanas (duplikat, celah, lonjakan)."""
    berkas = DERIVED / "integritas_bapanas.json"
    if not berkas.exists():
        return EnvelopeResponse(data={"tersedia": False}, meta=harga_service.meta_terkini())
    return EnvelopeResponse(
        data={"tersedia": True, "berkas": berkas.name, **_baca_json(berkas, {})},
        meta=harga_service.meta_terkini(),
    )


@router.get("/benchmark", response_model=EnvelopeResponse[Dict[str, Any]])
async def get_benchmark():
    """Evaluasi model sesuai DATA_PIPELINE §4.3: MAPE, sMAPE, MASE, Coverage80, Pinball."""
    berkas = sorted(DERIVED.glob("evaluasi_model_bapanas_*.json")) or sorted(
        DERIVED.glob("benchmark_ews_bapanas_*.json")
    )
    if not berkas:
        return EnvelopeResponse(
            data={"tersedia": False, "catatan": "belum ada benchmark"},
            meta=harga_service.meta_terkini(),
        )
    isi = _baca_json(berkas[-1], {})
    return EnvelopeResponse(
        data={"tersedia": True, "berkas": berkas[-1].name, **isi},
        meta=harga_service.meta_terkini(),
    )


