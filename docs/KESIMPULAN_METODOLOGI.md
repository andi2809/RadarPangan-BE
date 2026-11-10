# Kesimpulan Metodologi — Radar Pangan

Disusun 26 Okt 2026 dari bukti yang bisa diperiksa ulang (snapshot mentah, uji API, dan halaman
resmi SP2KP). Dokumen ini menjadi dasar keputusan implementasi berikutnya.

---

## Ringkasan satu paragraf

Kedua sumber yang kita pakai adalah **hasil pemantauan administratif**, bukan pengukuran pasar
yang ideal. PIHPS (BI) mengukur **harga pasar** harian di 9 kab/kota Jawa Barat; SP2KP (Kemendag)
memantau **514 kab/kota** tetapi sebagian serinya menempel pada **angka acuan**. Karena itu nilai
sebuah sumber tidak ditentukan oleh jumlah wilayah, melainkan oleh **kesesuaiannya dengan
pertanyaan yang diajukan**. Implementasi kita harus memisahkan lapisan, bukan mencampurnya.

---

## 1. Tiga kesimpulan besar

### 1.1 Tidak ada "harga yang benar" — ada "harga untuk pertanyaan apa"
| Pertanyaan | Sumber yang tepat | Bukti |
|---|---|---|
| Apakah harga pasar melampaui HET? | PIHPS | beras pasar Rp15.400–16.600 vs HET 13.500 (+10,7% s/d +23,0%) |
| Apakah daerah melaporkan harga di atas acuan? | SP2KP | 27/27 wilayah; beras 11 wilayah persis Rp13.500 |
| Berapa harga Minyakita menurut pemerintah? | SP2KP | varian Minyakita Rp15.700 (HET), flat 6 hari |

### 1.2 Datar bukan berarti stabil — datar adalah sinyal kualitas data
- Beras SP2KP: **rentang Rp0 selama 6 hari**, dan sebaran antarwilayah tetap **10,0%**.
- Cabai SP2KP: bergerak **Rp5.000** dalam 6 hari.
- Harga pasar nyata tidak pernah sedatar itu → kuat dugaan nilainya **diisi dari angka acuan**,
  bukan hasil pengamatan transaksi.
- Implikasi: kita bisa membedakan "dilaporkan dari pasar" vs "diketik dari acuan" **hanya dengan
  mengukur variasi** — tanpa perlu tahu isi formulir petugas.

### 1.3 Trade-off cakupan vs sinyal bersifat struktural
27/27 wilayah dengan angka datar **bukan** peningkatan kualitas EWS dibanding 9 wilayah yang
bergerak. Menambah sumber terus-menerus tidak menyelesaikan ini; yang menyelesaikan adalah
**memisahkan lapisan dan memberi label peran**.

---

## 2. Fakta teknis yang sudah terverifikasi

| Hal | Temuan | Cara verifikasi |
|---|---|---|
| Cakupan PIHPS Jabar | 9 dari 27 kab/kota (7 kota, 2 kabupaten) | panggilan `GetRefRegency` tipe harga 1–4; seluruh tipe produsen kosong |
| Akhir pekan | 24 dari 85 hari kalender kosong, **semuanya Sabtu–Minggu** | audit snapshot 3 Agu–26 Okt |
| SP2KP kab/kota | 27/27 wilayah, 5 komoditas, termasuk Minyakita | endpoint `export-area-daily-excel` level=2 |
| Level pasar SP2KP | identik dengan level kab/kota | uji `pasar_id=163` (Pasar Cibinong) |
| Metodologi nasional | HNT = rata-rata **terbobot geometrik**, bobot SBH 2022 (BPS) | halaman resmi "Tentang SP2KP" |
| Fungsi resmi SP2KP | data harga, **early warning**, **pemetaan disparitas**, dasar intervensi | idem |
| Klasifikasi beras | Medium, Premium, **SPHP**, Indikasi Geografis (empat sub-jenis) | idem |
| Kepatuhan HET (PIHPS) | 9 wilayah berstatus kritis (>+10%) | backtest 60 hari |
| Daya beda status | Beras presisi 0,2%; cabai 61% (recall 93%, jeda 6 hari) | backtest ambang |

---

## 3. Lima perubahan implementasi

1. **Sub-komoditas beras.** Tambahkan `sub_komoditas` (`medium` | `sphp`) agar harga program
   tidak dibandingkan dengan harga pasar.
2. **Agregasi berbobot.** Untuk agregat provinsi/nasional, tiru HNT: **rata-rata terbobot
   geometrik** dengan bobot SBH 2022 — supaya angka kita sebanding dengan angka resmi.
3. **Kalender hari bursa.** Semua rata-rata/tren dihitung per hari pelaporan; Sabtu–Minggu tidak
   diinterpolasi; UI menyebut "hari bursa".
4. **Indikator per pertanyaan.** Kepatuhan HET (level) · sinyal dini (momentum, hanya komoditas
   yang bergerak) · disparitas antarwilayah (fungsi resmi SP2KP). Ambang per komoditas.
5. **Provenance per baris.** `sumber` + `jenis_harga` sudah ada; tambah `snapshot_id` dan
   `flat_days` (berapa hari berturut-turut harga tidak berubah).

---

## 4. Yang sudah vs belum

| Sudah | Belum |
|---|---|
| Snapshot mentah imutabel + `sha256` + `runs.jsonl` | Pemetaan sub-komoditas beras |
| Dua sumber dengan peran tegas (`sumber`, `jenis_harga`) | Agregasi terbobot geometrik (SBH 2022) |
| `pipeline/`: fetch PIHPS, fetch SP2KP, rekonsiliasi, backtest, disparitas | Penanda `flat_days` dan `snapshot_id` per baris |
| 26 tes (integritas data, determinisme, perilaku sumber) | Scheduler harian (usul: GitHub Actions) |
| Laporan warga tidak lagi disimulasikan | Halaman "Kualitas Data" di dashboard |

---

## 5. Yang **tidak** akan kita lakukan (dan alasannya)

- **Interpolasi wilayah kosong** — mengarang data; langsung terlihat saat demo.
- **Scraping massal situs pemerintah** — rapuh dan melanggar prinsip etika data.
- **Menambah sumber keempat** sebelum tiga yang ada dirapikan.
- **Menyamakan harga acuan dengan harga pasar** di UI, walau angkanya berdekatan.
- **Menampilkan "jumlah laporan warga"** sebelum ada kiriman nyata.

---

## 6. Mengapa dua sumber "laporan petugas" bisa berbeda

Kedua sumber sama-sama berasal dari pelaporan manusia, tetapi berbeda pada lima hal struktural:

| Aspek | PIHPS (BI) | SP2KP (Kemendag) |
|---|---|---|
| Institusi pelapor | Kantor perwakilan BI daerah | Dinas Perdagangan kab/kota |
| Definisi komoditas | grade spesifik (mis. Beras Kualitas Medium I) | "Beras Medium" (sub-jenis: Medium/Premium/SPHP/IG) |
| Pasar sampel | pasar di kota sampel (Jabar: 9) | "pasar pantau" yang ditunjuk dinas |
| Agregasi | rata-rata beberapa pasar per wilayah | satu angka per wilayah per hari |
| Pemanfaatan | kebijakan moneter | IPH / rakor pengendalian inflasi daerah |

### Bukti: keduanya sepakat ketika benar-benar mengukur harga pasar

Kota Bandung, 26 Okt 2026:

| Komoditas | PIHPS | SP2KP | Selisih |
|---|---|---|---|
| Cabai rawit merah | 81.500 | 79.500 | −2,5% |
| Bawang merah | 35.000 | 36.167 | +3,3% |
| Telur ayam ras | 26.250 | 25.833 | −1,6% |
| **Beras medium** | **15.600** | **13.500** | **−13,5%** |

**Kesimpulan:** selisih besar **bukan** derau pengukuran — pada tiga komoditas yang bergerak, kedua
sumber sepakat dalam 1–3%. Divergensi hanya muncul pada beras, tepat pada seri yang di SP2KP
datarnya ekstrem (11/27 wilayah persis Rp13.500 selama 6 hari). Karena itu diagnosis yang benar
adalah *"apa yang dilaporkan berbeda"*, bukan *"dua petugas melihat harga berbeda"*.

**Batas kejujuran:** penjelasan "petugas mengisi angka HET" adalah inferensi dari pola, bukan
pernyataan resmi. Yang terverifikasi adalah definisi komoditas, institusi pelapor, agregasi, dan
pola angkanya.


---

## 7. Koreksi 29 Okt 2026 — "PIHPS bergerak di semua komoditas" terlalu kuat

Setelah menambahkan metrik `flat_days` (jumlah observasi terakhir dengan harga sama), terlihat:

| Sumber | Beras | Cabai | Bawang | Telur | Minyak curah |
|---|---|---|---|---|---|
| PIHPS (median) | 37 | 0 | 5 | 3 | 35 |
| SP2KP (median) | 5* | 1 | 0 | 5* | 5* |

\* batas atas 5 karena SP2KP baru ditarik 6 hari bursa.

**Kesimpulan yang diperbarui:** yang benar-benar bergerak cepat adalah **cabai**; beras dan minyak
curah juga *lengket* bahkan pada PIHPS (median 35–37 hari bursa tanpa berubah). Karena itu EWS
harus fokus pada komoditas yang bergerak, dan untuk beras/minyak memakai **disparitas antarwilayah**
sebagai indikator, bukan perubahan level.

---

## 8. Uji kualitas dataset Bapanas (6 Nov 2026)

Dataset resmi Bapanas (surat 1014/TS.02.03/B.2/11/2026) diperiksa sebelum dipakai sebagai
sumber tunggal EWS. Hasil pengujian pada `data/paket/bapanas.csv.gz`:

| Pemeriksaan | Hasil |
|---|---|
| Baris konsumen | 158.708 (produsen 31.104) |
| Wilayah | 27 kab/kota |
| Komoditas | 6 |
| Hari | 1.014 hari (2024-01-01 → 2026-10-31) |
| **Kepadatan sel** | 158.708 / 164.268 = **96,6%** |
| Kepadatan per komoditas | 96,3%–96,9% (merata) |
| Lonjakan harian > 50% | 153 dari 158.546 transisi = **0,10%** |
| Duplikat (tanggal × wilayah × komoditas) | 0 |

Artinya: dataset **lengkap dan konsisten** — tidak ada lubang besar per komoditas, dan lonjakan
ekstrem sangat jarang (0,10%), sehingga layak dipakai tanpa imputasi.

### Perbandingan dengan sumber lama (26 Okt 2026, Kota Bandung)

| Komoditas | Bapanas | SP2KP | Selisih |
|---|---|---|---|
| Beras Medium | 13.500 | 13.500 | 0% |
| Cabai Rawit Merah | 86.667 | 79.500 | +9,0% |
| Bawang Merah | 35.000 | 36.167 | −3,2% |
| Telur Ayam Ras | 25.500 | 25.833 | −1,3% |

Kesimpulan: Bapanas dan SP2KP **tidak identik** meski keduanya resmi. Karena itu setiap angka
tetap membawa label sumber, dan penggantian sumber dicatat sebagai keputusan (`sumber=bapanas`).

---

## 9. Benchmark model prakiraan pada data Bapanas (6 Nov 2026)

Target: harga H+7 per kab/kota per komoditas. Data: `paket/bapanas.csv.gz`
(162 seri, 1.014 hari, 2024-01-01 → 2026-10-31). Validasi: rolling-origin, horizon 7,
8.214 evaluasi per model.

| Komoditas | naive | seasonal-7 | SES 0,35 | Holt | Holt-Winters |
|---|---|---|---|---|---|
| Bawang merah | **4,6%** | 7,4% | 5,3% | 6,4% | 6,4% |
| Beras medium | **0,0%** | 0,0% | 0,1% | 0,5% | 0,6% |
| Cabai rawit | **10,2%** | 14,6% | 11,1% | 13,0% | 13,1% |
| Minyak curah | **0,0%** | 0,0% | 0,2% | 0,7% | 0,7% |
| Minyak kemasan | **0,0%** | 0,0% | 0,3% | 0,8% | 1,0% |
| Telur | **1,3%** | 2,4% | 1,6% | 2,2% | 2,3% |

(MAPE median; MASE memberi urutan yang sama.)

Kesimpulan: **naive (harga terakhir) mengalahkan semua model** pada MAPE maupun MASE.
Pola musiman mingguan tidak menolong (seasonal-7 justru dua kali lebih buruk untuk bawang dan
cabai), karena pergerakan harian didominasi derau, bukan siklus.

Konsekuensi produk:
1. Proyeksi H+7 = harga terakhir + **pita empiris** (kuantil per komoditas).
2. Nilai tambah dipindah ke **ketidakpastian, gap kebijakan, dan peringatan** — bukan ke
   kompleksitas model.
3. Klaim "machine learning" tidak dipakai; tidak ada dasar empiris untuk itu pada data ini.


---

## Catatan 10 Nov 2026 — model prakiraan dicabut

Seluruh eksperimen prakiraan (naive, SES/Holt/HW, MLP, LightGBM, ensemble, pita kuantil, metrik evaluasi) **dihapus dari produk dan repo**. Dokumen ini dipertahankan sebagai catatan historis riset, bukan spesifikasi yang berlaku.
