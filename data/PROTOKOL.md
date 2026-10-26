# Protokol Pengukuran Data — Radar Pangan

Dokumen acuan tunggal untuk pertanyaan "angka ini artinya apa". Diperbarui 26 Okt 2026.
Setiap penambahan sumber **wajib** memperbarui dokumen ini.

## 1. Definisi harga per sumber

| Sumber | Apa yang diukur | Satuan | Level | Frekuensi |
|---|---|---|---|---|
| PIHPS BI (`price_type_id=1`) | harga pasar **tradisional**, agregat kab/kota | Rp/kg (atau Rp/liter) | kab/kota | harian bursa |
| SP2KP Kemendag (`/report/api/hnt`) | **HNT** — rata-rata nasional **tertimbang** konsumsi | Rp/kg | nasional | harian |
| SP2KP (`province-comparison`) | rata-rata **provinsi** | Rp/kg | provinsi | harian |
| SP2KP (`het-ha`) | HET/HA resmi pemerintah | Rp/kg | nasional/provinsi | per kebijakan |
| SP2KP Tabulasi Harga (**Tableau**) | harga per **kab/kota**, termasuk Minyakita | Rp/kg | kab/kota | harian |
| Panel Harga NFA | harga pasar rakyat per komoditas | Rp/kg | kab/kota (target) | harian |

**Konsekuensi:** angka PIHPS dan SP2KP **tidak setara**. PIHPS = harga kab/kota; SP2KP = agregat
tertimbang (nasional) atau provinsi. Membandingkannya hanya sah bila dinyatakan sebagai
"kab/kota vs agregat provinsi/nasional".

## 2. Cakupan dan bias yang terukur (snapshot 3 Agu – 26 Okt 2026)

- **Wilayah:** 9 dari 27 kab/kota — **7 kota, 2 kabupaten** (Kab. Cirebon, Kab. Tasikmalaya).
  Artinya hampir semua observasi berasal dari wilayah perkotaan (*urban skew*).
- **Hari:** rentang 85 hari kalender, hanya **61 tanggal** berisi data → **24 hari kosong**,
  dan polanya sistematis: **seluruh Sabtu dan Minggu** (mis. 8–9, 15–16, 22–23 Agu; 24–25 Okt).
- **Cakupan per wilayah:** 59–61 dari 61 tanggal (hampir lengkap; yang hilang = akhir pekan).
- **Beras medium 26 Okt:** median Rp15.600 (kisaran Rp14.950–16.600) vs HET Rp13.500 → **+15,6%**.

## 3. Konsekuensi metodologis (wajib dipatuhi)

1. **Jangan menghitung rata-rata kalender harian.** Deret hanya punya hari bursa; rata-rata
   mingguan/bulanan harus memakai *hari observasi*, bukan 7/30 hari.
2. **Model time-series harus menangani gap akhir pekan** (frekuensi observasi, bukan harian).
   Mengisi akhir pekan dengan interpolasi = mengarang data.
3. **Agregasi lintas wilayah memakai median**, bukan mean — 9 wilayah kita tidak mewakili
   Jawa Barat, dan mean mudah tertarik satu kota mahal.
4. **Setiap klaim "Jawa Barat" harus menyebut cakupan.** Kalimat yang benar:
   "9 kab/kota yang melapor ke PIHPS", bukan "Jawa Barat".
5. **Perbandingan dengan HET = kepatuhan kebijakan**, bukan sinyal dini. Untuk sinyal dini
   gunakan momentum (harga vs median 30 hari) — lihat `dokumen/HASIL_BACKTEST_EWS.md`.
6. **Nilai kosong tetap kosong.** `tidak_ada_data` bukan 0, bukan rata-rata, bukan interpolasi.

## 4. Tingkatan data (`tier`) dan kualitas (`kualitas`)

- `tier`: `kabkota` | `provinsi` | `nasional`
- `kualitas`: `aktual` (dilaporkan sumber) | `turunan` (agregasi/median lintas sumber) |
  `estimasi` (model, wajib disertai interval)

Aturan: `turunan` dan `estimasi` **tidak boleh** masuk ke lapisan peta "aktual" tanpa label.

## 5. Rujukan berkas

- Registry sumber: `data/registry.json`
- Jejak tarikan: `data/derived/runs.jsonl`
- Rekonsiliasi lintas sumber: `data/derived/rekonsiliasi_<tanggal>.json`
- Backtest EWS: `data/derived/backtest_<tanggal>.json`
- API: `GET /api/v1/meta/sumber`, `/meta/konsistensi`, `/meta/backtest`


## 6. Koreksi 26 Okt 2026 — SP2KP punya data kab/kota (di Tableau)

Halaman `sp2kp.kemendag.go.id/statistik/tabulasi-harga` menampilkan harga **per kabupaten/kota**
(mis. Kab. Bogor, Kab. Sukabumi, Kab. Cianjur, Kab. Bandung, Kab. Garut, Kab. Tasikmalaya) dan
**memuat Minyakita** (HET Rp15.700).

Mekanismenya bukan JSON API: halaman menanam **dashboard Tableau** (`analitik.kemendag.go.id`)
dan mengambil token publik dari `api-sp2kp.kemendag.go.id/report/api/tableau/token-harga-public`.
Token itu **bukan** Personal Access Token — percobaan `POST /api/2.8/auth/signin` dijawab
`400 missing credentials or site elements`, jadi tidak bisa dipakai untuk REST.

Konsekuensi:
1. Pernyataan sebelumnya "SP2KP hanya nasional/provinsi" **salah sebagai generalisasi**; yang benar,
   *JSON API*-nya hanya nasional/provinsi.
2. Data kab/kota layak dipakai **hanya lewat ekspor manual** (crosstab/CSV dari dashboard) —
   bukan scraping otomatis. Simpan sebagai snapshot bertanggal + catat di `runs.jsonl`.
3. Bila ekspor tersedia, cakupan bisa naik dari 9/27 ke seluruh kab/kota dan label Minyakita
   punya dasar data (bukan hanya HET).


## 7. Temuan 26 Okt 2026 — SP2KP bisa diotomasi, dan semantik harganya beda

Endpoint aplikasi (bukan Tableau) berhasil dipanggil:
`POST /report/api/average-price/export-area-daily-excel` (multipart form).
- `level=1` → agregat provinsi · `level=2` + `kode_kab_kota` → **kab/kota** · `level=3` + `pasar_id` → pasar
- Hasil 26 Okt: **27/27 kab/kota**, 5 komoditas, termasuk **Minyakita** (Rp15.700)

**Peringatan semantik (penting untuk status):** seri **"Beras Medium"** SP2KP bukan harga pasar bebas.
Sebaran 26 Okt: **11 dari 27 wilayah persis Rp13.500** (nilai HET), sisanya Rp12.667–14.000.
Bandingkan dengan PIHPS "Beras Kualitas Medium I" di wilayah yang sama: Rp15.400–16.600
(median selisih **−14,3%**). Jadi SP2KP beras ≈ **harga program/HET**, PIHPS ≈ **harga pasar**.

Konsekuensi: memakai SP2KP untuk beras akan membuat peta tampak "aman" (mendekati HET),
sedangkan PIHPS menunjukkan "+15,6% di atas HET". Keduanya benar untuk pertanyaan berbeda.
Wajib dibedakan lewat field `jenis_harga`: `pasar` (PIHPS) vs `program` (SP2KP beras).
Untuk cabai/bawang/telur/minyak, selisih median vs PIHPS hanya −6,2% / +0,0% / −1,0%.
