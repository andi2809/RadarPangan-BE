# Hasil Backtest EWS — Radar Pangan

Data: snapshot PIHPS, 3 Agu – 26 Okt 2026 (60 hari), 9 kab/kota, 5 komoditas.
Definisi: **alarm** = status kritis (selisih vs HET/HAP > 10%); **kejadian** = harga naik ≥ 3%
dalam 7 hari ke depan. Sampel: 478 observasi per komoditas.

## Sinyal level (selisih terhadap HET/HAP)

| Komoditas | TP | FP | FN | Presisi | Recall | Jeda deteksi |
|---|---|---|---|---|---|---|
| Beras medium | 1 | 470 | 1 | **0,2%** | 50% | 7 hari |
| Cabai rawit merah | 277 | 177 | 21 | **61,0%** | 93% | 6 hari |
| Bawang merah | 25 | 141 | 98 | 15,1% | 20,3% | 5 hari |
| Telur ayam ras | 0 | 0 | 81 | – | 0% | – |
| Minyak goreng curah | 0 | 478 | 0 | 0% | – | – |

**Bacaan:** sinyal level **tidak punya daya beda** untuk beras dan minyak — harganya nyaris
selalu di atas HET (beras +14–23%, minyak +42%), sehingga "kritis" menyala terus dan tidak
memberi informasi baru. Hanya cabai yang benar-benar informatif (presisi 61%, recall 93%,
jeda 6 hari). Telur "buta" karena acuan dinamis membuat selisih selalu kecil.

## Sinyal momentum (harga vs median 30 hari sebelumnya)

| Ambang | Presisi rata-rata | Recall rata-rata | F1 |
|---|---|---|---|
| ≥1% | 14,1% | 37,7% | **43,3** |
| ≥2% | 23,3% | 35,4% | 41,6 |
| ≥3% | 22,7% | 33,9% | 40,1 |

**Bacaan:** momentum lebih seimbang antar komoditas (F1 ≈ 43 pada ambang 1%), tetapi presisi
rendah — banyak lonjakan kecil yang padam sendiri.

## Implikasi produk (rekomendasi)

1. **Pisahkan dua lapisan di UI:**
   - *Status kebijakan*: harga vs HET/HAP → menjawab "apakah harga melampaui acuan pemerintah".
   - *Sinyal dini*: momentum (harga vs median 30 hari) → menjawab "apakah sedang naik cepat".
   Jangan mencampur keduanya dalam satu label "kritis".
2. **Ambang perlu per-komoditas**, bukan satu angka: cabai layak ambang lebih ketat karena
   sinyalnya kuat; beras/minyak butuh indikator lain (disparitas antarwilayah, bukan level).
3. **Jangan klaim akurasi.** Sampel kecil (9 wilayah, 60 hari) — laporkan presisi/recall apa adanya.

## Batasan

- Hanya 9 dari 27 wilayah; semua kota/kabupaten yang melapor ke PIHPS.
- 24–25 Okt tidak ada data (hari tanpa laporan).
- Kejadian didefinisikan ≥3%/7 hari; definisi lain akan mengubah angka.
- Backtest mengukur **kinerja ambang**, bukan kualitas produk.


## Lampiran — Rekonsiliasi dua benchmark resmi (26 Okt 2026)

| Komoditas | Median 9 kab/kota | Provinsi PIHPS | Selisih | Provinsi SP2KP | Selisih |
|---|---|---|---|---|---|
| Beras medium | 15.600 | 15.850 | **−1,58%** | 13.262 | +17,63% |
| Cabai rawit merah | 67.500 | 76.500 | −11,76% | 71.009 | −4,94% |
| Bawang merah | 33.750 | 33.450 | +0,90% | 31.414 | +7,44% |
| Telur ayam ras | 25.400 | 25.500 | −0,39% | 25.506 | −0,42% |
| Minyak goreng curah | 22.350 | 21.600 | +3,47% | 19.865 | +12,51% |

Bacaan: terhadap **sumber yang sama** (PIHPS), 4 dari 5 komoditas sepakat dalam ±3,5% —
bukti bahwa agregasi kab/kota kita konsisten. Selisih besar hanya pada cabai (komoditas
paling volatil) dan pada perbandingan dengan **SP2KP** yang memakai penimbangan berbeda
(HNT berbobot konsumsi, bukan harga pasar kab/kota).
