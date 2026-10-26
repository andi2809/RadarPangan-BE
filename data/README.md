# Katalog Data — Radar Pangan

Aturan: **setiap dataset dicatat di sini** — sumber, URL, tanggal tarikan, cakupan, dan
keterbatasan. Tanpa entri di sini, data tidak boleh dipakai di UI.

---

## 1. `raw/pihps_jabar_2026-08-01_2026-10-23.csv`

| | |
|---|---|
| Sumber | **PIHPS Bank Indonesia** — `bi.go.id/hargapangan` (kanal harga pasar tradisional per daerah) |
| Endpoint | `GET /hargapangan/WebSite/TabelHarga/GetGridDataDaerah` |
| Parameter kunci | `comcat_id, price_type_id=1, province_id=12, regency_id=<ID PIHPS>, tipe_laporan=1, start_date, end_date` |
| Tanggal tarik | 2026-10-23 |
| Periode data | 2026-08-01 s/d 2026-10-23 (60 tanggal, hari kerja saja) |
| Baris | 2.700 (9 kab/kota × 5 komoditas × 60 tanggal) |
| Kolom | `tanggal, regency_id_pihps, wilayah, komoditas, harga_rp, sumber` |
| Satuan | Rupiah per **kg** (kecuali bila sumber menyatakan lain) |
| Pengolah | `pipeline/pihps_fetch.py` |

### Cakupan (penting!)

- PIHPS hanya menyediakan **9 dari 27 kab/kota** Jawa Barat untuk pasar tradisional
  (`GetRefRegency?ref_prov_id=12&price_type_id=1`): Kota Bandung, Kota Bekasi, Kota Bogor,
  Kota Cirebon, Kota Depok, Kota Sukabumi, Kota Tasikmalaya, Kab. Cirebon, Kab. Tasikmalaya.
- **18 kab/kota lain tidak punya data** → di UI wajib tampil `status="tidak_ada_data"`,
  **tidak boleh** diimputasi dari provinsi/tetangga.
- Akhir pekan sering kosong (contoh: 17–18 Okt tidak ada baris).

### Komoditas

| Kode internal | Nama PIHPS | ID |
|---|---|---|
| `beras_medium` | Beras Kualitas Medium I | `com_3` |
| `cabai_rawit_merah` | Cabai Rawit Merah | `com_16` |
| `bawang_merah` | Bawang Merah | `com_11` |
| `telur_ayam_ras` | Telur Ayam Ras Segar | `com_10` |
| `minyakita` | **TIDAK ADA di PIHPS** | — |

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
Harga pasar PIHPS di 9 kab/kota Jabar berkisar **Rp15.400–16.600/kg** (23 Okt 2026) —
artinya **+14% s/d +23% di atas HET**.

Konsekuensi: dengan ambang yang dikunci (kritis > +10%), **seluruh 9 wilayah berstatus `kritis`**.
Ini bukan bug perhitungan, ini temuan lapangan: HET tidak mencerminkan harga pasar saat ini.
Perlu keputusan tim: (a) tampilkan apa adanya (jujur & kuat untuk narasi transparansi),
atau (b) tambahkan acuan dinamis (median 90 hari) sebagai pembanding di UI.

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
