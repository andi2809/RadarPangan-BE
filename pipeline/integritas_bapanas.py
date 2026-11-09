"""Pemeriksaan integritas paket Bapanas (data/paket/bapanas.csv.gz).

Keluaran: data/derived/integritas_bapanas.json
Pemeriksaan: duplikat, harga tidak positif, tanggal masa depan, celah tanggal,
lonjakan harian > 50%, serta cakupan wilayah x komoditas.
"""

from __future__ import annotations

import csv
import datetime as dt
import gzip
import json
import pathlib
import statistics as st
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parents[1]
PAKET = ROOT / "data" / "paket" / "bapanas.csv.gz"
REF = ROOT / "data" / "referensi" / "umk_jabar_2026.csv"
OUT = ROOT / "data" / "derived" / "integritas_bapanas.json"

AMBANG_LONJAKAN = 0.5
CELAH_MAKS_HARI = 3


def main() -> int:
    wilayah_ref = {r["nama_wilayah"] for r in csv.DictReader(REF.open(encoding="utf-8"))}
    kunci: set[tuple[str, str, str, str]] = set()
    seri: dict[tuple[str, str], dict[dt.date, int]] = defaultdict(dict)
    duplikat = 0
    tidak_positif = 0
    masa_depan = 0
    wilayah_asing = 0

    hari_ini = dt.date(2026, 11, 9)
    with gzip.open(PAKET, "rt", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            tanggal = dt.date.fromisoformat(r["tanggal"])
            harga = int(r["harga_rp"]) if (r.get("harga_rp") or "").isdigit() else 0
            if r["wilayah"] not in wilayah_ref:
                wilayah_asing += 1
                continue
            if harga <= 0:
                tidak_positif += 1
                continue
            if tanggal > hari_ini:
                masa_depan += 1
            k = (r["tanggal"], r["wilayah"], r["komoditas"], r["tingkat"])
            if k in kunci:
                duplikat += 1
                continue
            kunci.add(k)
            if r["tingkat"] == "konsumen":
                seri[(r["wilayah"], r["komoditas"])][tanggal] = harga

    celah_besar = []
    lonjakan = 0
    total_transisi = 0
    for (wilayah, komoditas), data in seri.items():
        tanggal = sorted(data)
        for a, b in zip(tanggal, tanggal[1:]):
            total_transisi += 1
            if (b - a).days > CELAH_MAKS_HARI:
                celah_besar.append({"wilayah": wilayah, "komoditas": komoditas,
                                   "dari": a.isoformat(), "ke": b.isoformat(), "hari": (b - a).days})
            if abs(data[b] - data[a]) / data[a] > AMBANG_LONJAKAN:
                lonjakan += 1

    komoditas = sorted({k for (_w, k) in seri})
    kepadatan = []
    for kom in komoditas:
        pasangan = [1 for (_w, k) in seri if k == kom]
        kepadatan.append({"komoditas": kom, "seri": len(pasangan)})

    hasil = {
        "tanggal_periksa": hari_ini.isoformat(),
        "berkas": PAKET.name,
        "jumlah_seri_konsumen": len(seri),
        "jumlah_wilayah": len({w for (w, _k) in seri}),
        "jumlah_komoditas": len(komoditas),
        "duplikat": duplikat,
        "harga_tidak_positif": tidak_positif,
        "tanggal_masa_depan": masa_depan,
        "wilayah_tidak_dikenal": wilayah_asing,
        "celah_lebih_3_hari": len(celah_besar),
        "contoh_celah": celah_besar[:5],
        "lonjakan_harian_lebih_50pct": lonjakan,
        "total_transisi": total_transisi,
        "persen_lonjakan": round(lonjakan / total_transisi * 100, 3) if total_transisi else None,
        "seri_per_komoditas": kepadatan,
        "lulus": all(v == 0 for v in (duplikat, tidak_positif, masa_depan, wilayah_asing)),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(hasil, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"ok -> {OUT.name}")
    for k in ("jumlah_seri_konsumen", "jumlah_wilayah", "duplikat", "harga_tidak_positif",
              "tanggal_masa_depan", "wilayah_tidak_dikenal", "celah_lebih_3_hari",
              "lonjakan_harian_lebih_50pct", "persen_lonjakan", "lulus"):
        print(f"  {k:32s} {hasil[k]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
