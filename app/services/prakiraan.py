"""Prakiraan harga 7 hari: titik = harga terakhir (naive), pita = kuantil empiris.

Bukti pemilihan (walk-forward, 180 seri, 105.771 evaluasi, horizon 7):
- naive paling akurat di hampir semua komoditas (bawang 4,3–5,0%; cabai 8,0–12,0%;
  telur 1,8–1,9%); SES/Holt/Holt-Winters semuanya lebih buruk;
- drift 3 titik (implementasi lama) justru terburuk (cabai SP2KP 20,0%).
Pita sigma hanya mencakup 69–75%, karena itu dipakai kuantil empiris
(`pipeline/pita_prakiraan.py` → `data/derived/pita_prakiraan.json`), cakupan uji 84,5%.
"""

from __future__ import annotations

import json
import math
import pathlib
from statistics import pstdev
from typing import Iterable, Optional

HORIZON = 7
Z_95 = 1.96
JENDELA_VOLATILITAS = 30
PITA_JSON = pathlib.Path(__file__).resolve().parents[2] / "data" / "derived" / "pita_prakiraan.json"

_pita_cache: Optional[dict] = None


def _pita() -> dict:
    global _pita_cache
    if _pita_cache is None:
        try:
            _pita_cache = json.loads(PITA_JSON.read_text(encoding="utf-8")).get(
                "per_sumber_komoditas", {}
            )
        except (OSError, ValueError):
            _pita_cache = {}
    return _pita_cache


def pita_untuk(sumber: str | None, komoditas: str) -> Optional[tuple[float, float]]:
    """(q10, q90) perubahan 7 hari; None bila belum terkalibrasi."""
    data = _pita()
    for kunci in (f"{sumber}|{komoditas}", f"pihps|{komoditas}", f"sp2kp|{komoditas}"):
        if kunci in data:
            return data[kunci]["q10"], data[kunci]["q90"]
    return None


def volatilitas(nilai: list[int], jendela: int = JENDELA_VOLATILITAS) -> float:
    potong = nilai[-jendela:] if len(nilai) > jendela else nilai
    ret = [
        (potong[i] - potong[i - 1]) / potong[i - 1]
        for i in range(1, len(potong))
        if potong[i - 1] > 0
    ]
    return pstdev(ret) if len(ret) > 1 else 0.0


def prakiraan_h7(
    seri: Iterable[tuple[str, int]],
    flat_days: int = 0,
    komoditas: str | None = None,
    sumber: str | None = None,
) -> Optional[dict]:
    """Prakiraan H+7: titik = harga terakhir; pita = kuantil empiris (fallback sigma)."""
    titik = list(seri)
    if len(titik) < 2:
        return None
    nilai = [v for _t, v in titik]
    harga = nilai[-1]
    pita = pita_untuk(sumber, komoditas) if komoditas else None
    if pita:
        q10, q90 = pita
        metode_pita = "kuantil_empiris"
    else:
        lebar = Z_95 * volatilitas(nilai) * math.sqrt(HORIZON)
        q10, q90 = -lebar, lebar
        metode_pita = "sigma"
    return {
        "harga_prediksi_h7_rp": harga,
        "batas_bawah_rp": round(harga * (1 + q10)),
        "batas_atas_rp": round(harga * (1 + q90)),
        "volatilitas_harian": round(volatilitas(nilai), 4),
        "metode": "naive",
        "metode_pita": metode_pita,
        "pita_persen": [round(q10 * 100, 1), round(q90 * 100, 1)],
        "titik_dasar": len(nilai),
    }


def dalam_pita(harga: int, prakiraan: dict) -> bool:
    return prakiraan["batas_bawah_rp"] <= harga <= prakiraan["batas_atas_rp"]
