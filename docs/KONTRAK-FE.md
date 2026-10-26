# Kontrak Integrasi Front End ↔ API

**Untuk:** Andi (Front End / Next.js Dashboard)
**Dari:** Abyan · **Tanggal:** 25 Okt 2026
**Status API:** jalan & teruji lokal (8 endpoint, `pytest` 7/7 lulus). **Belum di-deploy** — menunggu ACC Vercel.

---

## 1. Base URL

| Lingkungan | Nilai |
|---|---|
| Lokal | `http://127.0.0.1:8000` (`uvicorn app.main:app --port 8000`) |
| Produksi | `<menyusul setelah deploy Vercel>` |

Pasang di FE sebagai env: `NEXT_PUBLIC_API_BASE` (default ke fixtures bila kosong).

## 2. Endpoint yang tersedia

| Method | Path | Isi |
|---|---|---|
| GET | `/api/health` | status layanan |
| GET | `/api/v1/publik/ringkasan-landing` | agregat untuk landing |
| GET | `/api/v1/komoditas` | 5 komoditas + acuan |
| GET | `/api/v1/wilayah` | 27 kab/kota Jabar (+ UMK, garis kemiskinan, populasi, centroid) |
| GET | `/api/v1/peta/status?komoditas=&tanggal=&layer=aktual\|h7` | array status per wilayah |
| GET | `/api/v1/wilayah/{kode}/ringkasan?komoditas=` | detail + histori 14 hari + prakiraan H+7 |
| GET | `/api/v1/laporan-warga/sekitar?lat=&lng=&komoditas=` | harga sekitar + progres klaster |
| POST | `/api/v1/laporan-warga` | kirim laporan (butuh header `X-API-Key`) |
| POST | `/api/v1/ai/briefing` | AI Policy Advisor (butuh `GEMINI_API_KEY` di server) |

Semua respons GET memakai amplop `{ ok, data, meta }`.

## 3. Peta field: mock FE → API

### 3.1 `regions.json` → `GET /api/v1/wilayah`

| FE (mock) | API | Catatan |
|---|---|---|
| `id` | `id` / `kode_kemendagri` | sama |
| `codeBps` | `code_bps` | sama |
| `name` | `name` / `nama` | sama |
| `type` | `type` (KABUPATEN/KOTA) | FE pakai huruf besar |
| `provinceName` | `province_name` | sama |
| `umk2026` | `umk_2026_rp` | **nama berbeda** |
| `garisKemiskinan` | `garis_kemiskinan_rp` | **nama berbeda** |
| `populasi` | `populasi` | sama |
| `centroid: {lat, lng}` | `lat`, `lng` (number) | **bentuk berbeda** |

### 3.2 `commodities.json` → `GET /api/v1/komoditas`

| FE | API |
|---|---|
| `hargaAcuanRp` | `harga_acuan_rp` |
| `jenisAcuan` | `jenis_acuan` (`HET`/`HAP`/`DINAMIS_MEDIAN_90H`) |
| `id`, `name`, `category`, `satuan`, `deskripsi` | sama |

### 3.3 `telemetry.json` → `GET /api/v1/peta/status`

**Perbedaan bentuk yang paling penting:**

- Mock FE: objek bersarang `{ [commodityId]: { [regionId]: {...} } }`
- API: **array datar** per komoditas → `data: StatusPetaItem[]`

| FE (`currentPrice.*`) | API |
|---|---|
| `hargaAktualRp` | `harga_aktual_rp` |
| `hargaAcuanRp` | `harga_acuan_rp` |
| `selisihPersen` | `selisih_persen` |
| `selisihRp` | *(tidak ada)* — hitung di FE: `harga_aktual_rp - harga_acuan_rp` |
| `status` | `status` (`aman`/`waspada`/`kritis`/`turun`/`tidak_ada_data`) |
| `movingAvg7d` | *(tidak ada)* — pakai `history_14d` di endpoint detail |
| `ews_score` | `ews_score` / `skor_ews` |

### 3.4 Histori & prakiraan → `GET /api/v1/wilayah/{kode}/ringkasan`

| FE | API |
|---|---|
| `history14d[]` | `history_14d[]` (alias: `seri_historis[]`) |
| `forecast7d[]` | `prakiraan[]` (berisi `tanggal, harga_rp, batas_bawah_rp, batas_atas_rp`) |
| `currentPrice` | field datar di `data` (`harga_aktual_rp`, `status`, dst.) |

### 3.5 `crowdsource.json` → `GET /api/v1/laporan-warga/sekitar`

| FE | API |
|---|---|
| `consensusMedianHarga` | `klaster.harga_konsensus_rp` |
| `totalReports` | `klaster.jumlah_laporan` |
| `statusKonsensus` | `klaster.status` (`belum_terverifikasi`/`sedang_berjalan`/`terverifikasi`) |
| `lat`, `lng` | `laporan[].jarak_m` (jarak, bukan koordinat) + `pusat_pencarian` |

## 4. Dua cara menyambung (pilih satu)

**A. Adapter di FE (rekomendasi, ±30 menit).**
Buat `src/lib/api.ts` yang memetakan snake_case → camelCase dan mengubah `StatusPetaItem[]`
menjadi struktur `telemetry` yang sudah dipakai komponen. Keuntungan: API tetap kanonik,
FE tidak perlu diubah banyak.

**B. Minta API menambah alias camelCase.**
Bisa saya tambahkan (`umk2026`, `garisKemiskinan`, `hargaAcuanRp`, `centroid{lat,lng}`).
Konsekuensi: respons lebih gemuk dan ada dua sumber nama field → rawan bingung.

## 5. Catatan yang menghemat waktu

- Angka acuan **sudah sama** dengan mock FE: beras `HET 13.500`, cabai `HAP 45.000`,
  bawang `HAP 32.000`, telur `DINAMIS 29.500`, minyak `HET 15.700`.
- Kode komoditas: API memakai `minyakita` (kompatibel dengan mock FE) dan menerima
  alias `minyak_goreng_curah` dari pipeline.
- Selalu sediakan fallback: kalau `fetch` gagal / API cold start, pakai `src/data/mock/*`
  dan tampilkan badge `mode_data` dari `meta`.
- Data PIHPS saat ini hanya mencakup **9 dari 27** kab/kota → wilayah lain harus
  tampil `tidak_ada_data`, jangan diwarnai tebakan.
