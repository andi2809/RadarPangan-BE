"""Harga acuan pemerintah (HET/HAP) — satu sumber: data/referensi/het_hap.csv.

Menggantikan peta `acuan_map` yang sebelumnya ditulis terpisah di beberapa router.
Rentang (min–max) disimpan karena beberapa HAP ditetapkan sebagai rentang, bukan angka tunggal.
"""

from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path

REF = Path(__file__).resolve().parents[2] / "data" / "referensi" / "het_hap.csv"

_ALIAS = {"minyakita": "minyak_goreng_kemasan"}


@lru_cache(maxsize=1)
def _muat() -> dict[str, dict]:
    hasil: dict[str, dict] = {}
    if not REF.exists():
        return hasil
    with REF.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            hasil[row["commodity_id"]] = {
                "acuan_rp": int(row["harga_acuan_rp"]),
                "min_rp": int(row["harga_acuan_min_rp"]),
                "max_rp": int(row["harga_acuan_max_rp"]),
                "jenis": row["jenis_acuan"],
                "tingkat": row["tingkat"],
                "satuan": row["satuan"],
                "dasar_hukum": row["dasar_hukum"],
                "catatan": row["catatan"],
            }
    return hasil


def untuk(komoditas: str) -> dict | None:
    return _muat().get(_ALIAS.get(komoditas, komoditas))


def acuan_rp(komoditas: str, bawaan: int = 0) -> int:
    data = untuk(komoditas)
    return data["acuan_rp"] if data else bawaan


def jenis(komoditas: str, bawaan: str = "HET") -> str:
    data = untuk(komoditas)
    return data["jenis"] if data else bawaan


def semua() -> dict[str, dict]:
    return dict(_muat())
