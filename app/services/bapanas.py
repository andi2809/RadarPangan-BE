"""Sumber utama EWS: dataset resmi Badan Pangan Nasional (tingkat konsumen).

Berkas: data/paket/bapanas.csv.gz (hasil pipeline/bapanas_import.py).
Wilayah tanpa data tidak dikarang — pemanggil mengembalikan `tidak_ada_data`.
"""

from __future__ import annotations

import csv
import gzip
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
PAKET = DATA_DIR / "paket" / "bapanas.csv.gz"

_ALIAS = {"minyakita": "minyak_goreng_kemasan"}


def _wilayah(nama: str) -> str:
    return " ".join(str(nama).lower().replace(".", "").split())


def _kode(komoditas: str) -> str:
    return _ALIAS.get(komoditas, komoditas)


@lru_cache(maxsize=1)
def _muat() -> dict:
    harga: dict[tuple[str, str], dict[str, int]] = {}
    if not PAKET.exists():
        return {"harga": {}}
    with gzip.open(PAKET, "rt", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if (row.get("tingkat") or "konsumen") != "konsumen":
                continue
            nilai = (row.get("harga_rp") or "").strip()
            if not nilai.isdigit():
                continue
            kunci = (_wilayah(row["wilayah"]), _kode(row["komoditas"]))
            harga.setdefault(kunci, {})[row["tanggal"]] = int(nilai)
    return {"harga": {k: sorted(v.items()) for k, v in harga.items()}}


def seri(nama_wilayah: str, komoditas: str, limit: int | None = None) -> list[tuple[str, int]]:
    data = _muat()["harga"].get((_wilayah(nama_wilayah), _kode(komoditas)), [])
    return data[-limit:] if limit else list(data)


def terakhir(nama_wilayah: str, komoditas: str) -> tuple[str, int] | None:
    data = seri(nama_wilayah, komoditas)
    return data[-1] if data else None


def cakupan() -> dict:
    muat = _muat()
    wilayah = {w for (w, _k) in muat["harga"]}
    tanggal = [t for s in muat["harga"].values() for t, _ in s]
    return {
        "sumber": "bapanas",
        "jumlah_seri": len(muat["harga"]),
        "jumlah_wilayah": len(wilayah),
        "periode": (min(tanggal), max(tanggal)) if tanggal else None,
    }


def meta_terkini() -> dict:
    cak = cakupan()
    return {
        "tanggal_data": cak["periode"][1] if cak["periode"] else None,
        "sumber": ["Badan Pangan Nasional"],
        "mode_data": "nyata" if cak["jumlah_seri"] else "demo",
    }
