"""Log jalur distribusi data (append-only).

Setiap tarikan sumber dicatat sebagai satu baris JSONL di `data/derived/runs.jsonl`:
run_id, sumber, mulai, selesai, jumlah_baris, status, berkas, sha256, pesan.

Dipakai oleh pipeline (pihps_fetch, rekonsiliasi) dan dibaca oleh endpoint
`/api/v1/meta/sumber` supaya kesegaran data bisa diperiksa publik.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = ROOT / "data" / "derived" / "runs.jsonl"


def _sha256(path: Path) -> str | None:
    if not path or not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for blok in iter(lambda: fh.read(65536), b""):
            h.update(blok)
    return h.hexdigest()


def mulai(sumber: str) -> dict:
    return {
        "run_id": uuid.uuid4().hex[:12],
        "sumber": sumber,
        "mulai": datetime.now(timezone.utc).isoformat(),
    }


def selesai(ctx: dict, *, status: str, berkas: Path | None = None,
            jumlah_baris: int | None = None, pesan: str = "") -> dict:
    catatan = {
        **ctx,
        "selesai": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "berkas": berkas.name if berkas else None,
        "sha256": _sha256(berkas) if berkas else None,
        "jumlah_baris": jumlah_baris,
        "pesan": pesan[:300],
    }
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(catatan, ensure_ascii=False) + "\n")
    return catatan


def terakhir_per_sumber() -> dict[str, dict]:
    """Run terakhir untuk setiap sumber (dibaca dari ekor berkas)."""
    if not LOG_PATH.is_file():
        return {}
    hasil: dict[str, dict] = {}
    with LOG_PATH.open(encoding="utf-8") as fh:
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
