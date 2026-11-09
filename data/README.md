# Katalog Data — Radar Pangan

Aturan: **setiap dataset dicatat di sini** — sumber, URL, tanggal tarikan, cakupan, dan
keterbatasan. Tanpa entri di sini, data tidak boleh dipakai di UI.

> **Acuan normatif: [`PROTOKOL.md`](PROTOKOL.md)** — definisi "harga" per sumber, aturan agregasi
> (median, bukan mean), dan bias terukur. Dokumen ini katalog; PROTOKOL yang mengikat.

---

## 1. Snapshot PIHPS (banyak berkas, digabung loader)

| Berkas | Periode | Baris |
|---|---|---|
| `raw/pihps_jabar_2026-08-01_2026-10-23.csv` | 3 Agu – 23 Okt | 2.700 |
| `raw/pihps_jabar_2026-10-24_2026-10-26.csv` | 26 Okt | 45 |
| `raw/pihps_jabar_2026-10-26_2026-10-26.csv` | 26 Okt (tarikan ulang) | 45 |

Loader `app/services/harga.py` **menggabungkan semua snapshot**; untuk kunci yang sama
(`tanggal, wilayah, komoditas`), berkas dengan nama paling akhir menang. Total: **61 tanggal
unik, 3 Agu – 26 Okt 2026**.

| | |
|---|---|
| Sumber | **PIHPS Bank Indonesia** — `bi.go.id/hargapangan` (kanal harga pasar tradisional per daerah) |
| Endpoint | `GET /hargapangan/WebSite/TabelHarga/GetGridDataDaerah` |
| Parameter kunci | `comcat_id, price_type_id=1, province_id=12, regency_id=<ID PIHPS>, tipe_laporan=1, start_date, end_date` |
| Tanggal tarik terakhir | 2026-10-26 |
| Periode data | 2026-08-03 s/d 2026-10-26 (**61 tanggal**, hari bursa saja) |
| Baris | 2.790 baris gabungan (9 kab/kota × 5 komoditas × 61 tanggal + tarikan ulang) |
| Kolom | `tanggal, regency_id_pihps, wilayah, komoditas, harga_rp, sumber` |
| Satuan | Rupiah per **kg** (kecuali bila sumber menyatakan lain) |
| Pengolah | `pipeline/pihps_fetch.py` |

### Cakupan (penting!)

- PIHPS hanya menyediakan **9 dari 27 kab/kota** Jawa Barat untuk pasar tradisional
  (`GetRefRegency?ref_prov_id=12&price_type_id=1`): Kota Bandung, Kota Bekasi, Kota Bogor,
  Kota Cirebon, Kota Depok, Kota Sukabumi, Kota Tasikmalaya, Kab. Cirebon, Kab. Tasikmalaya.
- **18 kab/kota lain tidak punya data** → di UI wajib tampil `status="tidak_ada_data"`,
  **tidak boleh** diimputasi dari provinsi/tetangga.
- **Akhir pekan tidak pernah ada data.** Dari 85 hari kalender (3 Agu – 26 Okt), hanya 61 yang
  berisi; **24 hari kosong dan semuanya Sabtu–Minggu**. Jangan menginterpolasi.

### Komoditas

| Kode internal | Nama PIHPS | ID |
|---|---|---|
| `beras_medium` | Beras Kualitas Medium I | `com_3` |
| `cabai_rawit_merah` | Cabai Rawit Merah | `com_16` |
| `bawang_merah` | Bawang Merah | `com_11` |
| `telur_ayam_ras` | Telur Ayam Ras Segar | `com_10` |
| `minyak_goreng_curah` | Minyak Goreng Curah | `com_17` |

Catatan: kode `minyakita` masih dipakai di API (kompatibilitas FE) dan dipetakan ke
`minyak_goreng_curah`; labelnya menunggu keputusan tim.

⚠️ **Temuan yang bertentangan dengan keputusan terkunci:** Andi mengunci komoditas
`minyakita`, tetapi PIHPS tidak memisahkan Minyakita. Yang tersedia: `Minyak Goreng Curah`
(`com_17`), `Minyak Goreng Kemasan Bermerk 1` (`com_18`), `Bermerk 2` (`com_19`).
Perlu keputusan: ganti kode menjadi `minyak_goreng_curah`/`kemasan`, atau tunggu Bapanas
(pusat datanya sedang maintenance).

---

## 2. Referensi PIHPS yang bisa dipakai tanpa tarikan

| Endpoint | Isi |
|---|---|
| `GetRefPriceType` | 4 tipe harga: Pasar Tradisional (1), Pasar Modern (2), Pedagang Besar (3), **Produsen (4)** |
| `GetRefProvince` | 38 provinsi (Jawa Barat = `12`) |
| `GetRefRegency?ref_prov_id=&price_type_id=` | Kab/kota **yang ada datanya** per provinsi & tipe harga |
| `GetRefCommodityAndCategory` | 31 item (kategori + komoditas) beserta ID |
| `GetRefMarket?ref_regency_id=&price_type_id=` | Daftar pasar per kab/kota |

Catatan teknis: portal BI memerlukan **cookie sesi** dan header `X-Requested-With`.
Tanggal wajib **ISO (`YYYY-MM-DD`)** — format `DD/MM/YYYY` menghasilkan HTTP 302.
`tipe_laporan=1` = harian; `tipe_laporan=2` = periode bulanan.
`GetGridDataKomoditas` hanya mengembalikan level provinsi; data kab/kota harus lewat
`GetGridDataDaerah` dengan `regency_id` (ID internal PIHPS, **bukan** kode BPS/Kemendagri).

---

## 3. Temuan penting: harga pasar di atas HET

HET beras medium **Zona 1 (Jawa) = Rp13.500/kg** (Perbadan 5/2024 jo. kenaikan Agustus 2025).
Harga pasar PIHPS di 9 kab/kota Jabar: **26 Okt 2026** median **Rp15.600/kg**
(kisaran Rp14.950–16.600) — artinya **+15,6% di atas HET** (median; rentang +10,7% s/d +23,0%).

Konsekuensi: dengan ambang yang dikunci (kritis > +10%), **seluruh 9 wilayah berstatus `kritis`**.
Ini bukan bug perhitungan, ini temuan lapangan: HET tidak mencerminkan harga pasar saat ini.
**Sudah diukur, bukan diperdebatkan:** backtest 60 hari menunjukkan sinyal level-vs-HET
**tidak punya daya beda** untuk beras (presisi 0,2%) dan minyak (0%) — hanya cabai yang
informatif (presisi 61%, recall 93%, jeda 6 hari). Detail: [`../docs/HASIL_BACKTEST_EWS.md`](../docs/HASIL_BACKTEST_EWS.md).
Rekomendasi: pisahkan *status kebijakan* (vs HET) dari *sinyal dini* (momentum).

## Catatan Minyak Goreng (temuan 26 Okt 2026)

PIHPS **tidak punya entri "Minyakita"**. Yang tersedia di `GetRefCommodityAndCategory`:
`Minyak Goreng` (kategori `cat_9`), `Minyak Goreng Curah` (`com_17`),
`Minyak Goreng Kemasan Bermerk 1` (`com_18`), `Minyak Goreng Kemasan Bermerk 2` (`com_19`).

Uji 26 Okt 2026 (`tipe_laporan=1`, tipe harga Pasar Tradisional):

| Wilayah | com_17 (curah) | com_18 (kemasan 1) | com_19 (kemasan 2) |
|---|---|---|---|
| Kota Bandung | 23.400 | 23.400 | 23.400 |
| Kota Bekasi | 22.350 | 22.350 | 22.350 |
| Kota Bogor | 23.300 | 23.300 | 23.300 |

Angka **identik** untuk ketiga id → sumber melaporkan satu seri minyak lalu menduplikasinya.
**Konsekuensi:** Minyakita tidak dapat dipisahkan dari data PIHPS; label "Minyakita" pada
API/FE tidak didukung sumber, terlebih harga 23.400 jauh di atas HET Minyakita 15.700.
Keputusan penamaan (id & label) menunggu tim.

### Sumber pembanding: SP2KP Kemendag (diuji 26 Okt 2026)

`https://api-sp2kp.kemendag.go.id` — **terbuka tanpa API key**, harian.
Granularitas: **nasional (HNT) + provinsi**, bukan kab/kota.

| Endpoint | Isi |
|---|---|
| `/report/api/hnt?tanggal=YYYY-MM-DD` | HNT semua komoditas pada satu tanggal |
| `/report/api/average-price/province-comparison?tanggal=…&variant_id=…` | harga per provinsi |
| `/report/api/het-ha/latest?variant_id=…` | HET/HA resmi |

Varian yang relevan (HNT 26 Okt 2026): Beras Medium `52` → 13.999 · Cabai Rawit Merah `10`
→ 77.108 · Bawang Merah `13` → 32.959 · Telur Ayam Ras `25` → 26.571 · Minyak Goreng Sawit
Curah `16` → 19.494 · **Minyakita `18` → 15.844** (HET resmi **Rp15.700**, berlaku 2025-07-01).

**Koreksi catatan sebelumnya:** "Minyakita tidak ada di sumber mana pun" tidak tepat.
PIHPS BI dan Panel Harga Bapanas tidak memisahkannya, tetapi **Kemendag (SP2KP) punya**
varian Minyakita — hanya pada level nasional/provinsi, bukan kab/kota.


---

## 4. `raw/sp2kp_jabar_<tanggal>.csv` (impor ekspor Tableau)

| | |
|---|---|
| Sumber | SP2KP Kemendag — dashboard **Tabulasi Harga** (`sp2kp.kemendag.go.id/statistik/tabulasi-harga`) |
| Cara ambil | **ekspor manual** (tombol Download di halaman area/Tableau) — berkas `.csv` maupun `.xlsx` didukung |
| Pengolah | `pipeline/sp2kp_import.py` (`make sp2kp-import BERKAS=...`) |
| Kolom | `tanggal, wilayah, komoditas, harga_rp, sumber` |
| Level | **kabupaten/kota** (termasuk `minyakita`) |
| Catatan | token publik Tableau bukan PAT → REST signin ditolak; jangan scraping |

Aturan: berkas ini **tidak** dicampur otomatis ke loader PIHPS. Pemakaiannya harus eksplisit
(analisis atau penambahan layer) agar provenance dua sumber tidak tertukar.


---

## 5. `raw/sp2kp_jabar_<start>_<end>.csv` (tarikan otomatis API SP2KP)

| | |
|---|---|
| Sumber | SP2KP Kemendag, endpoint `POST /report/api/average-price/export-area-daily-excel` |
| Pengolah | `pipeline/sp2kp_fetch.py` (`make sp2kp-fetch START=… END=…`) |
| Level | **kab/kota** (`level=2`), 27 wilayah Jawa Barat |
| Kolom | `tanggal, wilayah, komoditas, harga_rp, sumber` |
| Hasil 19–26 Okt 2026 | 810 baris (27 wilayah × 5 komoditas × 6 hari bursa) |
| Catatan | `skip_sat_sun=true` → Sabtu/Minggu tidak ditarik |

⚠️ **Semantik:** `beras_medium` dari SP2KP mendekati **harga program/HET** (11/27 wilayah persis
Rp13.500), bukan harga pasar bebas seperti PIHPS. Lihat `PROTOKOL.md` bagian 7.


---

## 6. `derived/gabungan_harga.csv` (ekspor siap pakai)

| | |
|---|---|
| Pengolah | `pipeline/gabung_ekspor.py` (`make gabung`) |
| Isi | gabungan PIHPS + SP2KP, satu baris per (tanggal, wilayah, komoditas, sumber) |
| Kolom | `tanggal, wilayah, komoditas, harga_rp, sumber, jenis_harga` |
| Hasil 26 Okt 2026 | 3.515 baris · 27 wilayah · 3 Agu–26 Okt (PIHPS 2.705 · SP2KP 810) |

Dipakai untuk berbagi data ke tim FE/analisis: label `sumber` dan `jenis_harga` ikut terbawa,
sehingga penggabungan tidak menghilangkan provenance.


---

## 7. `derived/harga_utama.csv` — satu tabel untuk front end

| | |
|---|---|
| Pengolah | `pipeline/harga_utama.py` (`make harga-utama`) |
| Aturan | PIHPS dipakai bila ada; bila tidak, SP2KP menambal. **Tidak ada perata-rataan dua sumber.** |
| Kolom | `tanggal, kode_kemendagri, wilayah, komoditas, harga_rp, sumber, jenis_harga` |
| Hasil 29 Okt 2026 | 3.303 baris · 27 wilayah · sumber: PIHPS 2.705 + SP2KP 598 · jenis: pasar 2.923 + acuan 380 |

Konsekuensi yang harus disadari: untuk **beras**, 9 wilayah berasal dari PIHPS (`pasar`) dan 18
wilayah dari SP2KP (`acuan`) — peta akan memperlihatkan dua kelompok. Itu bukan bug, melainkan
batas data; UI disarankan membedakan pola/warna untuk `acuan`.


---

## 8. Arsip historis (backfill 30 Okt 2026)

| Berkas | Baris | Wilayah | Rentang | Ukuran |
|---|---|---|---|---|
| `raw/pihps_jabar_2023-10-26_2026-10-26.csv` | 35.235 | 9 | 2023-10-26 → 2026-10-26 | ±2,4 MB |
| `raw/sp2kp_jabar_2024-04-01_2026-10-26.csv` | 83.086 | 27 | 2024-04-01 → 2026-10-30 | 5,0 MB |

Catatan:
- SP2KP **hanya menyimpan ±2,5 tahun** (uji 2024-01 = kosong, 2024-04 = ada) → arsip ini wajib dijaga.
- PIHPS tersedia sejak 2018, tetapi arsip dibatasi 3 tahun agar perbandingan acuan tetap sebanding.
- `derived/pita_prakiraan.json` dihitung dari dua arsip di atas (`make pita`), bukan saat request.
- Bundel Vercel **tidak** memuat `derived/*.csv` (6–7 MB); lihat `vercel.json`.


---

## 9. `paket/*.csv.gz` — berkas yang ikut ke serverless

| | |
|---|---|
| Pengolah | `pipeline/paket_kompres.py` (`make paket`) |
| Isi | `pihps.csv.gz` (35.235 baris) dan `sp2kp.csv.gz` (83.086 baris), sudah digabung & dideduplikasi |
| Ukuran | **0,40 MB** total (dari 7,4 MB CSV mentah) |
| Dipakai | `app/services/harga.py` dan `fakta.py` membaca paket ini bila ada; jika tidak, jatuh ke `data/raw/` |

Catatan pengukuran (lokal):

| | raw | paket gzip |
|---|---|---|
| Ukuran berkas | 7,4 MB | **0,40 MB** |
| Waktu parse PIHPS | 114 ms | 123 ms |
| Waktu parse SP2KP | 255 ms | 280 ms |

Artinya: gzip **tidak** mempercepat parse (sedikit lebih lambat karena dekompresi), tetapi
memangkas ukuran bundel 18× — itulah yang memengaruhi unduhan/init fungsi serverless.
Bundel Vercel dibatasi lewat `vercel.json` ke `{app,data/paket,data/referensi,data/derived/*.json}`.


---

## 10. `paket/bapanas.csv.gz` — sumber utama EWS

| | |
|---|---|
| Asal | Surat Badan Pangan Nasional No. 1014/TS.02.03/B.2/11/2026 (5 Nov 2026) |
| Importer | `pipeline/bapanas_import.py` (`make bapanas`) |
| Isi | 189.812 baris · 27 kab/kota · konsumen 158.708 + produsen 31.104 · 2024-01-01 → 2026-10-31 |
| Komoditas | 6 (termasuk Minyak Goreng Kemasan) |
| Ukuran | 0,71 MB (gzip) |

Berkas Excel mentah **tidak** ada di repo (repo publik); tersimpan privat di
`dokumen/data-bapanas-privat/`. PIHPS dan SP2KP tetap disimpan sebagai pembanding.


---

## 11. Analitik Bapanas (6 Nov 2026)

`pipeline/disparitas.py` kini juga menghitung sumber **bapanas** (paket konsumen,
180 hari terakhir agar berkas tetap ringan) dan menulisnya ke `derived/disparitas.json`
di samping `sp2kp` dan `pihps`.

Sebaran antarwilayah (median, 180 hari terakhir):

| Komoditas | Sebaran median |
|---|---|
| Bawang merah | 56,9% |
| Cabai rawit | 53,1% |
| Minyak kemasan | 40,3% |
| Minyak curah | 25,0% |
| Beras medium | 15,5% |
| Telur | 13,9% |

Endpoint `/api/v1/meta/disparitas` mengembalikan kunci `bapanas` beserta dua sumber lama.


---

## 12. `referensi/het_hap.csv` — skema baru (9 Nov 2026)

Kolom: `commodity_id, name, jenis_acuan, tingkat, harga_acuan_min_rp, harga_acuan_max_rp,
harga_acuan_rp, satuan, dasar_hukum, catatan`.

`harga_acuan_rp` adalah titik yang dipakai perhitungan (untuk HAP berupa rentang, dipakai titik
tengah); `min/max` disimpan agar UI bisa menampilkan rentang resmi. Sumber: Kepbadan 299/2025,
Kepbadan 529/2024, Kepmendag 1028/2024, Perbadan 12/2024.
