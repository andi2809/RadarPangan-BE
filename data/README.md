# Katalog Data — Radar Pangan

Aturan: **setiap dataset dicatat di sini** — sumber, URL, tanggal tarikan, cakupan, dan
keterbatasan. Tanpa entri di sini, data tidak boleh dipakai di UI.

---

## 1. `raw/pihps_jabar_2026-10-20_2026-10-23.csv`

| | |
|---|---|
| Sumber | **PIHPS Bank Indonesia** — `bi.go.id/hargapangan` (kanal harga pasar tradisional per daerah) |
| Endpoint | `GET /hargapangan/WebSite/TabelHarga/GetGridDataDaerah` |
| Parameter kunci | `comcat_id, price_type_id=1, province_id=12, regency_id=<ID PIHPS>, tipe_laporan=1, start_date, end_date` |
| Tanggal tarik | 2026-10-23 |
| Periode data | 2026-10-20 s/d 2026-10-23 (4 hari, hari kerja) |
| Baris | 144 (9 kab/kota × 4 komoditas × 4 hari) |
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
