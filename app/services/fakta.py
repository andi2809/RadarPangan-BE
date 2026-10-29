"""Layanan fakta harga yang sadar-sumber (PIHPS dan SP2KP).

Prinsip yang dijaga:
- Setiap fakta membawa `sumber` dan `jenis_harga` (`pasar` atau `acuan`).
- PIHPS = hasil survei pasar tradisional → `pasar`.
- SP2KP = pemantauan daerah; bergerak hanya untuk cabai & bawang → `pasar`,
  sedangkan beras/telur/minyakita praktis menempel acuan → `acuan`.
- Wilayah tanpa data tidak dikarang; pemanggil mengembalikan `tidak_ada_data`.
"""

from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
RAW_DIR = DATA_DIR / "raw"

POLA = {"pihps": "pihps_jabar_*.csv", "sp2kp": "sp2kp_jabar_*.csv"}

# Komoditas SP2KP yang harganya benar-benar bergerak (lihat PROTOKOL bagian 7-9).
SP2KP_BERGERAK = {"cabai_rawit_merah", "bawang_merah"}


def jenis_harga(sumber: str, komoditas: str) -> str:
    if sumber == "sp2kp" and komoditas not in SP2KP_BERGERAK:
        return "acuan"
    return "pasar"


def _wilayah(nama: str) -> str:
    return " ".join(str(nama).lower().replace(".", "").split())


@lru_cache(maxsize=8)
def muat(sumber: str) -> dict:
    """{ (wilayah, komoditas): [(tanggal, harga)] } gabungan semua snapshot sumber itu."""
    pola = POLA.get(sumber)
    if not pola:
        raise ValueError(f"sumber tidak dikenal: {sumber}")

    data: dict[tuple[str, str], dict[str, int]] = {}
    for path in sorted(RAW_DIR.glob(pola)):
        with path.open(encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                nilai = (row.get("harga_rp") or "").strip()
                if not nilai.isdigit():
                    continue
                kunci = (_wilayah(row["wilayah"]), row["komoditas"])
                data.setdefault(kunci, {})[row["tanggal"]] = int(nilai)
    return {k: sorted(v.items()) for k, v in data.items()}


def seri(nama_wilayah: str, komoditas: str, sumber: str, limit: int | None = None) -> list[tuple[str, int]]:
    data = muat(sumber).get((_wilayah(nama_wilayah), komoditas), [])
    return data[-limit:] if limit else list(data)


def terakhir(nama_wilayah: str, komoditas: str, sumber: str) -> tuple[str, int] | None:
    data = seri(nama_wilayah, komoditas, sumber)
    return data[-1] if data else None


def cakupan(sumber: str) -> dict:
    data = muat(sumber)
    wilayah = {w for (w, _k) in data}
    tanggal = [t for seri in data.values() for t, _h in seri]
    return {
        "sumber": sumber,
        "jumlah_wilayah": len(wilayah),
        "periode": (min(tanggal), max(tanggal)) if tanggal else None,
    }


def flat_days(seri: list[tuple[str, int]]) -> int:
    """Berapa hari bursa berturut-turut harga terakhir tidak berubah.

    0 = berubah pada observasi terakhir; 5 = lima observasi terakhir sama.
    Indikator kualitas: seri yang panjang 'flat' biasanya angka acuan, bukan harga pasar.
    """
    if not seri:
        return 0
    terakhir = seri[-1][1]
    sama = 0
    for _tanggal, harga in reversed(seri):
        if harga != terakhir:
            break
        sama += 1
    return max(0, sama - 1)
