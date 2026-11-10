# Rumus & Perhitungan Radar Pangan

Penjelasan bahasa manusia untuk seluruh angka yang tampil di sistem. Versi PDF: `dokumen/RUMUS_RADAR_PANGAN.pdf`.
Berlaku 9 November 2026. Semua contoh dihitung dari sistem yang berjalan.

## 1. Ringkasan

Radar Pangan mengolah harga pangan harian dari **Badan Pangan Nasional** (27 kabupaten/kota Jawa Barat,
6 komoditas, 1 Januari 2024 – 31 Oktober 2026). Keluarannya: status harga (warna peta), skor risiko 0–100,
status, skor risiko, dan perbandingan antarwilayah.

Prinsip: **tidak mengarang angka**. Wilayah tanpa data ditandai “tidak ada data”; celah tidak diimputasi;
angka selalu disertai sumber dan acuan resmi.

## 2. Sumber data

**Satu-satunya sumber harga: dataset resmi Badan Pangan Nasional** (surat 1014/TS.02.03/B.2/11/2026)
— 27/27 kabupaten/kota, 6 komoditas, harian 2024-01-01 – 2026-10-31. Tidak ada sumber harga pembanding.

Yang dibandingkan dengan harga Bapanas: **(1)** acuan pemerintah HET/HAP, dan **(2)** **data riil hari ini**
dari laporan warga.

## 3. Harga acuan (HET/HAP)

| Komoditas | Acuan | Rentang resmi | Dasar hukum |
|---|---|---|---|
| Beras medium | 13.500 | 13.500 | Kepbadan 299/2025 (Zona Jawa) |
| Bawang merah | 39.000 | 36.500–41.500 | Perbadan 12/2024 |
| Cabai rawit merah | 48.500 | 40.000–57.000 | Perbadan 12/2024 |
| Telur ayam ras | 30.000 | 30.000 | Kepbadan 529/2024 |
| Minyak goreng curah | 15.700 | 15.700 | Kepmendag 1028/2024 |

Untuk HAP berbentuk rentang, perhitungan memakai **titik tengah**; batas bawah–atas tetap ditampilkan.

## 4. Status harga

```
selisih% = (harga − acuan) / acuan × 100
> +10%  → kritis
+5..10% → waspada
−5..+5% → aman
< −5%   → turun
```

Contoh: cabai Kota Bandung Rp60.000 vs acuan Rp48.500 → +23,7% → **kritis**.

## 5. Skor EWS (0–100)

```
skor = 0,45 × deviasi + 0,35 × tren + 0,20 × daya beli

deviasi   = clamp((selisih% + 5) × 4, 0, 100)
tren      = clamp((laju Rp/hari ÷ laju normal) × 50 + 30, 0, 100)
            laju normal: cabai 300, beras 50, lainnya 150 Rp/hari
            tren = 0 bila harga tidak berubah ≥3 hari (flat_days ≥ 3)
daya beli = clamp((harga × berat bulanan) ÷ (UMK × 0,10) × 100, 0, 100)
            berat bulanan: beras 10 kg, lainnya 2 kg
```

Ambang risiko: ≥75 EXTREME · ≥55 HIGH · ≥35 MEDIUM · <35 LOW.

Contoh (cabai Kota Bandung, 31 Okt 2026): deviasi 100 · tren 24,5 · daya beli 27,2 → **skor 59**, EXTREME.

## 6. Disparitas antarwilayah

`(harga tertinggi − harga terendah) / harga terendah` per komoditas per tanggal.
Median 180 hari terakhir: bawang 56,9% · cabai 53,1% · minyak kemasan 40,3% · minyak curah 25,0% ·
beras 15,5% · telur 13,9%.

## 7. Kualitas data

Diperiksa setiap impor: duplikat, harga ≤ 0, tanggal masa depan, wilayah asing, celah > 3 hari,
lonjakan harian > 50%. Hasil 9 Nov 2026: 0 duplikat · 0 harga tidak valid · 0 tanggal masa depan ·
lonjakan 0,097% → lulus.

## 8. Batasan

1. Sumber harga tunggal Bapanas; HET/HAP dan UMK dipakai untuk penilaian, bukan untuk meramal.
2. Musim panen menjelaskan beda akurasi antar-komoditas, tetapi penyesuaian musiman memperburuk prakiraan 7 hari.
3. Prakiraan hanya untuk horizon 7 hari.
4. Laporan warga belum tersimpan permanen (masih di memori server).

## Lampiran — endpoint verifikasi

| Yang dicek | Alamat |
|---|---|
| Peta status + skor | `/api/v1/peta/status?sumber=bapanas` |
| Detail wilayah | `/api/v1/wilayah/32.73/ringkasan?komoditas=cabai_rawit_merah&sumber=bapanas` |
| Evaluasi model | `/api/v1/meta/benchmark` |
| Kualitas data | `/api/v1/meta/integritas` |
| Sebaran antarwilayah | `/api/v1/meta/disparitas` |
| Daftar sumber | `/api/v1/meta/sumber` |

> **Catatan:** seluruh bagian prakiraan (naive, pita, metrik evaluasi) dihapus pada 10 Nov 2026 atas keputusan produk. Sistem kini hanya menyajikan status, skor EWS, acuan, disparitas, dan kualitas data.
