"""Fetcher PIHPS Bank Indonesia — harga harian per kabupaten/kota (Jawa Barat).

Hasil penyelidikan 23 Okt 2026 (semua endpoint JSON, tanpa API key):

  GET /hargapangan/WebSite/TabelHarga/GetRefPriceType
      1=Pasar Tradisional, 2=Pasar Modern, 3=Pedagang Besar, 4=Produsen
  GET /hargapangan/WebSite/TabelHarga/GetRefProvince            -> Jawa Barat = 12
  GET /hargapangan/WebSite/TabelHarga/GetRefRegency?ref_prov_id=12&price_type_id=1
      -> daftar kab/kota yang ADA datanya (Jabar: 9 dari 27)
  GET /hargapangan/WebSite/TabelHarga/GetRefCommodityAndCategory
      -> com_1..com_N (mis. com_3 = "Beras Kualitas Medium I")
  GET /hargapangan/WebSite/TabelHarga/GetGridDataDaerah
      ?comcat_id=com_3&price_type_id=1&province_id=12&regency_id=30
      &tipe_laporan=1&start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
      -> BARIS PER KOMODITAS untuk satu kab/kota (level 1 = agregat, level 2 = varian)
  GET /hargapangan/WebSite/TabelHarga/GetGridDataKomoditas
      -> hanya level provinsi (parameter regency diabaikan)

Catatan penting:
- `regency_id` di GetGridDataDaerah memakai ID internal PIHPS (bukan kode BPS/Kemendagri).
- `tipe_laporan=1` = tabel harian; `tipe_laporan=2` = periode bulanan.
- Tanggal WAJIB format ISO (YYYY-MM-DD); format DD/MM/YYYY menghasilkan 302.
- Sesi cookie + header X-Requested-With diperlukan.

Cara pakai:
    python pipeline/pihps_fetch.py --start 2026-10-16 --end 2026-10-23
Keluaran: data/raw/pihps_jabar_<start>_<end>.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import pathlib
import sys
import time
import urllib.parse
import urllib.request
from http.cookiejar import CookieJar

BASE = "https://www.bi.go.id/hargapangan"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/126 Safari/537.36"
JABAR_PROVINCE_ID = 12

# komoditas -> potongan nama yang dicari di GetRefCommodityAndCategory
TARGET_KOMODITAS = {
    "beras_medium": "Beras Kualitas Medium I",
    "cabai_rawit_merah": "Cabai Rawit Merah",
    "bawang_merah": "Bawang Merah",
    "telur_ayam_ras": "Telur Ayam Ras",
    "minyakita": "Minyakita",
}

_opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))


def _get(path: str, referer: str | None = None, tries: int = 3) -> dict:
    url = f"{BASE}{path}"
    req = urllib.request.Request(url, headers={"User-Agent": UA, "X-Requested-With": "XMLHttpRequest"})
    if referer:
        req.add_header("Referer", f"{BASE}{referer}")
    last: Exception | None = None
    for attempt in range(tries):
        try:
            with _opener.open(req, timeout=40) as resp:
                return json.loads(resp.read().decode("utf-8", "replace"))
        except Exception as exc:  # noqa: BLE001 - jaringan portal pemerintah sering lambat
            last = exc
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"gagal mengambil {path}: {last}")


def _warm_session() -> None:
    """Ambil cookie sesi dari halaman tabel (dibutuhkan portal BI)."""
    req = urllib.request.Request(
        f"{BASE}/TabelHarga/PasarTradisionalDaerah", headers={"User-Agent": UA}
    )
    with _opener.open(req, timeout=40) as resp:
        resp.read()


def _parse_rupiah(nilai: str) -> int | None:
    """'15,900' -> 15900 ; '-' / '' -> None"""
    if not nilai:
        return None
    bersih = str(nilai).replace(".", "").replace(",", "").strip()
    if not bersih.isdigit():
        return None
    return int(bersih)


def daftar_kabupaten() -> list[dict]:
    data = _get(
        f"/WebSite/TabelHarga/GetRefRegency?ref_prov_id={JABAR_PROVINCE_ID}&price_type_id=1",
        referer="/TabelHarga/PasarTradisionalDaerah",
    )
    return data.get("data", [])


def peta_komoditas() -> dict[str, str]:
    data = _get("/WebSite/TabelHarga/GetRefCommodityAndCategory").get("data", [])
    hasil: dict[str, str] = {}
    for kode, nama in TARGET_KOMODITAS.items():
        cocok = [d for d in data if d.get("cat_id") and nama.lower() in str(d.get("name", "")).lower()]
        if cocok:
            hasil[kode] = cocok[0]["id"]
    return hasil


def tarik_kabupaten(regency_id: int, comcat_id: str, start: str, end: str) -> dict[str, int | None]:
    """Kembalikan {tanggal: harga} untuk satu kab/kota & satu komoditas (baris agregat)."""
    q = urllib.parse.urlencode(
        {
            "comcat_id": comcat_id,
            "price_type_id": 1,
            "province_id": JABAR_PROVINCE_ID,
            "regency_id": regency_id,
            "tipe_laporan": 1,
            "showPasar": "true",
            "start_date": start,
            "end_date": end,
        }
    )
    data = _get(f"/WebSite/TabelHarga/GetGridDataDaerah?{q}", referer="/TabelHarga/PasarTradisionalDaerah")
    baris = data.get("data", [])
    if not baris:
        return {}
    # level 1 = agregat komoditas (harga rata-rata kab/kota), level 2 = varian
    agregat = next((b for b in baris if b.get("level") == 1), baris[0])
    hasil: dict[str, int | None] = {}
    for kunci, nilai in agregat.items():
        if kunci.count("/") == 2:  # kolom tanggal: dd/mm/yyyy
            d, m, y = kunci.split("/")
            hasil[f"{y}-{m}-{d}"] = _parse_rupiah(nilai)
    return hasil


def main() -> int:
    ap = argparse.ArgumentParser(description="Tarik harga PIHPS per kab/kota Jawa Barat")
    ap.add_argument("--start", required=True, help="YYYY-MM-DD")
    ap.add_argument("--end", required=True, help="YYYY-MM-DD")
    args = ap.parse_args()

    _warm_session()
    kab = daftar_kabupaten()
    kom = peta_komoditas()
    print(f"kab/kota tersedia di PIHPS: {len(kab)}")
    print(f"komoditas dipetakan: {len(kom)}/5 -> {kom}")
    if not kab or not kom:
        print("Tidak ada data referensi; hentikan.")
        return 1

    akar = pathlib.Path(__file__).resolve().parents[1]
    tujuan = akar / "data" / "raw" / f"pihps_jabar_{args.start}_{args.end}.csv"
    tujuan.parent.mkdir(parents=True, exist_ok=True)

    jumlah = 0
    with tujuan.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["tanggal", "regency_id_pihps", "wilayah", "komoditas", "harga_rp", "sumber"])
        for wilayah in kab:
            for kode, comcat_id in kom.items():
                try:
                    seri = tarik_kabupaten(wilayah["id"], comcat_id, args.start, args.end)
                except RuntimeError as exc:
                    print(f"  ! {wilayah['name']} / {kode}: {exc}")
                    continue
                for tanggal, harga in sorted(seri.items()):
                    w.writerow([tanggal, wilayah["id"], wilayah["name"], kode, harga, "pihps_bi"])
                    jumlah += 1
                time.sleep(1.5)  # sopan terhadap portal pemerintah
    print(f"selesai: {jumlah} baris -> {tujuan}")
    print("CATATAN: wilayah yang tidak muncul = tidak ada data di PIHPS (jangan diimputasi).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
