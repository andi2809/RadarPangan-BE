"""Indikator turunan dari seri harga (sumber tunggal: Bapanas)."""

from __future__ import annotations

from typing import Iterable


def flat_days(seri: Iterable[tuple[str, int]]) -> int:
    """Jumlah observasi terakhir berturut-turut dengan harga sama (0 = berubah terakhir)."""
    titik = list(seri)
    if not titik:
        return 0
    terakhir = titik[-1][1]
    sama = 0
    for _tanggal, harga in reversed(titik):
        if harga != terakhir:
            break
        sama += 1
    return max(0, sama - 1)


def sifat_seri(flat: int) -> str:
    """Turunan data: statis bila 3 observasi terakhir sama, selain itu bergerak."""
    return "statis" if flat >= 3 else "bergerak"


def metode_data(sumber: str | None = None) -> str:
    """Fakta asal angka: dataset resmi Bapanas."""
    return "resmi_bapanas"
