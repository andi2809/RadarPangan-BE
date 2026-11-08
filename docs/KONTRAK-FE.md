# Kontrak Integrasi Front End ↔ API

**Untuk:** Andi (Front End / Next.js Dashboard)
**Dari:** Abyan · **Diperbarui:** 26 Okt 2026
**Status API:** **live di produksi**, **13 rute** (`/docs`), `pytest` **18/18** lulus.

---

## 1. Base URL

| Lingkungan | Nilai |
|---|---|
| Produksi | `https://radar-pangan-server.vercel.app` |
| Dokumen | `https://radar-pangan-server.vercel.app/docs` · `/openapi.json` |
| Lokal | `http://127.0.0.1:8000` (`uvicorn app.main:app --port 8000`) |

Pasang di FE sebagai env `NEXT_PUBLIC_API_BASE`. **Selalu** sediakan fallback ke `fixtures/`
bila request gagal / cold start.

## 2. Endpoint yang tersedia

| Method | Path | Isi |
|---|---|---|
| GET | `/api/health` | status layanan |
| GET | `/api/v1/publik/ringkasan-landing` | agregat untuk landing (data nyata) |
| GET | `/api/v1/komoditas` | 5 komoditas + acuan |
| GET | `/api/v1/wilayah` | 27 kab/kota Jabar (+ UMK, garis kemiskinan, populasi, centroid) |
| GET | `/api/v1/peta/status?komoditas=&tanggal=&layer=aktual\|h7&sumber=bapanas\|pihps\|sp2kp\|utama` | array status per wilayah |
| GET | `/api/v1/wilayah/{kode}/ringkasan?komoditas=` | detail + histori 14 hari + prakiraan H+7 |
| GET | `/api/v1/laporan-warga/sekitar?lat=&lng=&komoditas=` | harga sekitar + progres klaster (simulasi) |
| POST | `/api/v1/laporan-warga` | kirim laporan |
| GET | `/api/v1/meta/sumber` | registry sumber + kesegaran + run terakhir |
| GET | `/api/v1/meta/konsistensi` | rekonsiliasi PIHPS vs SP2KP (per komoditas) |
| GET | `/api/v1/meta/backtest` | presisi/recall/jeda deteksi ambang EWS |
| GET | `/api/v1/meta/disparitas` | sebaran harga antarwilayah per hari |
| GET | `/` | info layanan (redirect ke `/docs`) |
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
| — | `sumber` (`pihps`/`sp2kp`) dan `jenis_harga` (`pasar`/`acuan`) — **wajib ditampilkan** sebagai badge |
| — | `rekomendasi_tindakan` & `risk_level` — **wajib ditampilkan**; dihitung backend (SSOT), jangan dihitung ulang di FE |
| — | `harga_prediksi_h7_rp` = **harga terakhir** (naive); bandingkan dengan `pita` — jangan tampilkan satu angka tanpa rentang |
| — | `flat_days` — berapa observasi terakhir harga tidak berubah (0 = berubah terakhir). Gunakan untuk memberi catatan "harga stabil N hari" atau menandai seri yang tampak seperti angka acuan |

### 3.4 Histori & prakiraan → `GET /api/v1/wilayah/{kode}/ringkasan`

| FE | API |
|---|---|
| `history14d[]` | `history_14d[]` (alias: `seri_historis[]`) |
| `forecast7d[]` | `prakiraan[]` (`tanggal, harga_rp, batas_bawah_rp, batas_atas_rp`) |
| `currentPrice` | field datar di `data` (`harga_aktual_rp`, `status`, dst.) |

### 3.5 `crowdsource.json` → `GET /api/v1/laporan-warga/sekitar`

| FE | API |
|---|---|
| `consensusMedianHarga` | `klaster.harga_konsensus_rp` |
| `totalReports` | `klaster.jumlah_laporan` |
| `statusKonsensus` | `klaster.status` (`belum_terverifikasi`/`sedang_berjalan`/`terverifikasi`) |
| `lat`, `lng` | `laporan[].jarak_m` + `pusat_pencarian` |

Endpoint ini **tidak lagi disimulasikan**. Daftar kosong sampai ada pengiriman nyata
(`peringatan_kualitas` memuat `BELUM_ADA_LAPORAN`), dan penyimpanan masih in-memory
(`LAPORAN_WARGA_PENYIMPANAN_SEMENTARA`) sehingga hilang saat layanan restart.
Tampilkan apa adanya — jangan mengisi angka contoh.

## 4. Dua cara menyambung (pilih satu)

**A. Adapter di FE (rekomendasi).** Buat `src/lib/api.ts` yang memetakan snake_case → camelCase dan
mengubah `StatusPetaItem[]` menjadi struktur `telemetry` komponen. API tetap kanonik.

**B. Minta API menambah alias camelCase.** Bisa, tetapi respons lebih gemuk dan ada dua sumber nama
field → rawan bingung.

## 4b. Kalau butuh satu tabel jadi (tanpa memilih sumber)

Gunakan `data/derived/harga_utama.csv` (`make harga-utama`): satu baris per wilayah × komoditas
× tanggal, dengan aturan **PIHPS prioritas, SP2KP menambal**. Kolom `sumber` dan `jenis_harga`
tetap ada — jangan dihapus saat memuat ke UI; itulah yang membedakan "harga pasar" dan "angka acuan".

## 5. Catatan yang menghemat waktu

- **Angka landing berubah** (26 Okt): kini dihitung dari data nyata → `jumlah_aman 0`,
  `jumlah_kritis 9`, `kestabilan_wilayah_pct 0.0`. Badge "aman" di FE harus ikut berubah.
- Acuan masih sama: beras `HET 13.500`, cabai `HAP 45.000`, bawang `HAP 32.000`,
  telur `DINAMIS 29.500`, minyak `HET 15.700`. Label **Minyakita vs Minyak Goreng Curah
  masih menunggu keputusan tim** — jangan hardcode di FE.
- Kode komoditas: API memakai `minyakita` dan menerima alias `minyak_goreng_curah`.
- `sumber=bapanas` (default) = dataset resmi Badan Pangan Nasional, **27/27 wilayah**,
  6 komoditas termasuk `minyak_goreng_kemasan`.
- `sumber=utama` = **satu tabel jadi**: PIHPS dipakai bila ada, SP2KP menambal sisanya.
  Memberi **27/27 wilayah**; tetap periksa `jenis_harga` per baris (beras: 9 `pasar`, 18 `acuan`).
- `sumber=sp2kp` memberi **27/27 wilayah**, tetapi untuk beras/telur/minyakita
  `jenis_harga = "acuan"` (angka menempel HET) — jangan diberi label "harga pasar".
  Cabai & bawang dari SP2KP tetap `pasar` karena memang bergerak.
- Selalu tampilkan `meta.mode_data` sebagai badge; bila `peringatan_kualitas` berisi
  `CAKUPAN_SEBAGIAN_9_DARI_27_WILAYAH`, tampilkan catatan cakupan.
- Data PIHPS hanya mencakup **9 dari 27** kab/kota → wilayah lain `tidak_ada_data`,
  jangan diwarnai tebakan.
- Status adalah **kepatuhan HET**, bukan sinyal dini. Bila FE ingin "sinyal dini",
  pakai `/api/v1/meta/backtest` sebagai rujukan kualitas, bukan menambah label baru sendiri.
