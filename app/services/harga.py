"""Akses harga nyata dari snapshot PIHPS (data/raw/pihps_jabar_*.csv).

Prinsip:
- Hanya membaca berkas hasil `pipeline/pihps_fetch.py` (data resmi PIHPS BI).
- Wilayah yang tidak ada di berkas **tidak dikarang**: pemanggil harus mengembalikan
  `status="tidak_ada_data"`.
- Komoditas `minyakita` dipetakan ke `minyak_goreng_curah` karena PIHPS tidak
  memisahkan Minyakita (lihat data/README.md).
"""

from __future__ import annotations

import csv
import gzip
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
RAW_DIR = DATA_DIR / "raw"
PAKET = DATA_DIR / "paket" / "pihps.csv.gz"

_ALIAS_KOMODITAS = {
    "minyakita": "minyak_goreng_curah",
    "minyak_goreng_curah": "minyak_goreng_curah",
}


def _kode(komoditas: str) -> str:
    return _ALIAS_KOMODITAS.get(komoditas, komoditas)


def _wilayah(nama: str) -> str:
    return " ".join(str(nama).lower().replace(".", "").split())


def _berkas_semua() -> list[Path]:
    if PAKET.exists():
        return [PAKET]
    return sorted(RAW_DIR.glob("pihps_jabar_*.csv"))


@lru_cache(maxsize=1)
def _muat() -> dict:
    """Gabungkan SEMUA snapshot CSV (bukan hanya yang terakhir).

    Snapshot boleh tumpang tindih; untuk (tanggal, wilayah, komoditas) yang sama,
    berkas dengan nama paling akhir menang (dianggap paling baru).
    """
    harga: dict[tuple[str, str], dict[str, int]] = {}
    berkas = _berkas_semua()
    for path in berkas:
        pembuka = gzip.open if path.suffix == ".gz" else open
        with pembuka(path, "rt", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                nilai = (row.get("harga_rp") or "").strip()
                if not nilai.isdigit():
                    continue
                kunci = (_wilayah(row["wilayah"]), _kode(row["komoditas"]))
                harga.setdefault(kunci, {})[row["tanggal"]] = int(nilai)

    seri_harga = {kunci: sorted(nilai.items()) for kunci, nilai in harga.items()}
    return {"harga": seri_harga, "sumber": [p.name for p in berkas]}


def seri(nama_wilayah: str, komoditas: str, limit: int | None = None) -> list[tuple[str, int]]:
    data = _muat()["harga"].get((_wilayah(nama_wilayah), _kode(komoditas)), [])
    return data[-limit:] if limit else list(data)


def terakhir(nama_wilayah: str, komoditas: str) -> tuple[str, int] | None:
    data = seri(nama_wilayah, komoditas)
    return data[-1] if data else None


def cakupan() -> dict:
    """Ringkasan cakupan data — dipakai untuk meta.peringatan_kualitas."""
    muat = _muat()
    wilayah = {w for (w, _k) in muat["harga"]}
    tanggal = [t for seri in muat["harga"].values() for t, _ in seri]
    return {
        "sumber": muat["sumber"],
        "jumlah_wilayah": len(wilayah),
        "periode": (min(tanggal), max(tanggal)) if tanggal else None,
    }


def meta_terkini(sumber: list[str] | None = None):
    """Meta standar berisi tanggal data terakhir + peringatan cakupan (satu sumber kebenaran)."""
    from ..schemas import Meta

    cak = cakupan()
    peringatan = ["DATA_PIHPS_SNAPSHOT"] if cak["sumber"] else ["SNAPSHOT_PIHPS_TIDAK_ADA"]
    if cak["sumber"] and cak["jumlah_wilayah"] and cak["jumlah_wilayah"] < 27:
        peringatan.append(f"CAKUPAN_SEBAGIAN_{cak['jumlah_wilayah']}_DARI_27_WILAYAH")
    return Meta(
        tanggal_data=cak["periode"][1] if cak["periode"] else None,
        sumber=sumber or ["PIHPS BI"],
        mode_data="nyata" if cak["sumber"] else "demo",
        peringatan_kualitas=peringatan,
    )
