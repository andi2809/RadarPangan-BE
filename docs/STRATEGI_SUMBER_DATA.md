# Strategi Sumber Data — Radar Pangan

Dokumen kerja, 26 Okt 2026. Menjawab: sumber mana yang paling lengkap, bagaimana menggabungkan
yang terpencar, dan bagaimana melacak jalur distribusi datanya.

## 1. Kenapa terasa terpencar (dan kenapa itu normal)

Data pangan Indonesia diproduksi berlapis: daerah (TPID/Dinas) → provinsi → kementerian/lembaga.
Tidak ada satu endpoint publik yang menyajikan **harian + kabupaten/kota + 5 komoditas + gratis**.
Yang paling mendekati "terpusat" adalah **Panel Harga NFA**, karena memang dirancang sebagai
agregator nasional — dan itulah yang aksesnya sedang kita ajukan.

Maka strategi yang benar bukan "cari satu sumber sempurna", melainkan **federasi sumber dengan
jejak asal yang eksplisit**. Itu juga yang akan dilakukan data engineer di industri.

## 2. Matriks sumber (hasil uji langsung, 26 Okt 2026)

| Sumber | Granularitas | Frekuensi | Akses | Cakupan Jabar | Catatan |
|---|---|---|---|---|---|
| PIHPS BI | kab/kota | harian | terbuka | **9/27** | dipakai sekarang |
| SP2KP Kemendag | nasional + provinsi | harian | terbuka | 1 provinsi | ada varian Minyakita |
| Portal dataset Bapanas | provinsi/bulanan | bulanan | unduh | parsial | Livewire, unduhan per dataset |
| BPS (webapi) | kab/kota (produsen) | bulanan | API key | 27 | bukan retail harian |
| Panel Harga / Web API NFA | kab/kota | harian | **API key** | target 27 | sedang diajukan |

Kesimpulan: **tidak ada yang lengkap sekarang**; yang paling berpotensi lengkap = NFA.

## 3. Arsitektur yang saya usulkan (federasi + lineage)

```
[Adapter PIHPS]  [Adapter SP2KP]  [Adapter Bapanas]  [Adapter NFA (nanti)]
        │               │                │                    │
        └──────────► RAW (snapshot imutabel, tanggal di nama berkas)
                              │
                     NORMALISASI (skema kanonik)
                              │
                     VALIDASI (skema + anomali + duplikat)
                              │
                     CANONICAL STORE (satu tabel fakta)
                              │
                     SERVING API (tier + sumber + snapshot_id)
```

**Skema fakta kanonik** (satu baris = satu observasi):

```
tanggal | kode_kemendagri | komoditas_kanonik | jenis_harga (konsumen|produsen|acuan)
harga | satuan | tier (kabkota|provinsi|nasional) | sumber | snapshot_id | fetched_at
kualitas (aktual|turunan|referensi)
```

Kuncinya: `tier` + `kualitas` membuat kita **tidak pernah** mencampur data kab/kota dengan
provinsi tanpa label. Ini yang membedakan proyek "rapi" dan "asal gabung".

## 4. "Sinkron antar sumber" — jadikan metrik, bukan asumsi

> **Pembaruan 26 Okt:** verifikasi lapangan (gold set) dibatalkan atas keputusan tim.
> Penggantinya: **benchmark resmi** — seri provinsi dari PIHPS sendiri (pembanding spasial
> sumber yang sama) dan seri provinsi SP2KP (pembanding lintas sumber). Keduanya gratis dan
> bisa direproduksi siapa pun.

Alih-alih berharap sumber cocok, **ukur ketidakcocokannya**:

- Ambil tanggal & komoditas yang ada di ≥2 sumber.
- Hitung: `selisih = (harga_kabkota_median − harga_provinsi) / harga_provinsi`.
- Simpan sebagai **laporan rekonsiliasi** harian: `tanggal, komoditas, sumber A, sumber B, selisih_%`.
- Tampilkan di UI sebagai indikator "konsistensi data" (hijau <5%, kuning 5–15%, merah >15%).

Efeknya: kita punya bukti kuantitatif bahwa data kita masuk akal, dan juri melihat praktik
data-quality yang jarang dilakukan peserta lain.

## 5. Melacak jalur distribusi data (lineage)

Tiga artefak kecil, dampak besar:

1. **`pipeline/registry.yaml`** — daftar sumber: URL, parameter, granularitas, jadwal, batas laju,
   pemilik, lisensi, kontak.
2. **`pipeline/runs.jsonl`** — log append-only setiap tarikan: `run_id, sumber, mulai, selesai,
   jumlah_baris, status, sha256_berkas, pesan_error`.
3. **`GET /api/v1/meta/sumber`** — endpoint publik yang menampilkan matriks cakupan, kesegaran
   terakhir, dan peringatan. Ini membuat "banyak sumber" menjadi **tergovernansi**, bukan disembunyikan.

Ditambah: setiap respons API menyertakan `sumber`, `tier`, dan `snapshot_id` per fakta (kita sudah
punya `sumber` di level meta; tinggal dinaikkan ke level baris).

## 6. Aturan fallback (harus eksplisit)

```
1. kab/kota aktual          → tampilkan
2. tidak ada → provinsi     → tampilkan dengan label "acuan provinsi"
3. tidak ada → nasional     → label "acuan nasional"
4. tidak ada sama sekali    → "tidak_ada_data" (jangan diinterpolasi)
```

## 7. Kontrol kualitas minimum

- **Freshness**: peringatkan bila snapshot > 24 jam.
- **Coverage**: hitung % wilayah berdata per komoditas (sudah ada).
- **Anomali**: lonjakan >20% hari-ke-hari ditandai, bukan dihapus.
- **Duplikat**: kunci natural `(tanggal, wilayah, komoditas)` unik; snapshot baru menimpa lama.
- **Integritas**: sha256 per snapshot di `runs.jsonl`.

## 8. Yang saya sarankan dikerjakan lebih dulu

1. `registry.yaml` + `runs.jsonl` + `GET /meta/sumber` (kecil, tanpa dependensi baru).
2. Skrip rekonsiliasi PIHPS vs SP2KP → laporan harian.
3. Naikkan `sumber`/`tier` ke level baris respons.
4. Nanti, saat NFA disetujui: tambahkan adapter NFA sebagai tier tertinggi, tanpa mengubah kontrak.

## 9. Yang sebaiknya TIDAK dilakukan

- Scraping massal situs pemerintah (rapuh + risiko etika/legal).
- Interpolasi 18 wilayah tanpa data (akan terlihat saat demo).
- Menyembunyikan asal data di balik satu angka agregat.
