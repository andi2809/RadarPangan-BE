# AGENTS.md — aturan kerja repo RadarPangan-Server

Konteks singkat: FastAPI untuk lomba **Web In Action 2026**, data harga pangan Jawa Barat.
API live di Vercel. Semua bahasa deliverable: **Indonesia**.

## Aturan wajib setiap commit

1. **Dokumentasi ikut commit.** Perubahan perilaku (endpoint, field respons, sumber data,
   ambang, cara menjalankan) wajib memperbarui:
   - `README.md` (tabel endpoint/status/data yang terdampak),
   - `docs/KONTRAK-FE.md` bila bentuk respons berubah,
   - `data/PROTOKOL.md` bila definisi/asal data berubah.
   Commit tanpa ini dianggap belum selesai.
2. **Jalankan `make test`** sebelum commit. Jangan melemahkan atau menghapus tes untuk membuatnya
   lulus; perbaiki kodenya.
3. **Kejujuran data tidak boleh dilanggar:** wilayah tanpa data → `tidak_ada_data`, bukan 0
   atau rata-rata. Setiap respons memuat `meta.mode_data` + `meta.peringatan_kualitas`.
4. **Jangan mengarang angka acuan.** HET/HAP hanya dari `data/referensi/het_hap.csv` atau regulasi
   resmi yang bisa ditunjukkan sumbernya.
5. **Snapshot mentah imutabel.** Jangan menimpa `data/raw/pihps_jabar_*.csv`; tarik berkas baru.
   Setiap tarikan dicatat lewat `pipeline/runlog.py` (`data/derived/runs.jsonl`).
6. **Deploy:** `make deploy`. Jangan menambah `rewrites` di `vercel.json`; `includeFiles` wajib
   memuat `data/**`.

## Yang perlu keputusan Abyan/Andi (jangan diputuskan sendiri)

- Label komoditas **Minyakita vs Minyak Goreng Curah** (menunggu Andi).
- Mengubah **kontrak API** yang sudah dipakai front end.
- Menambah **dependensi baru** (mis. `pandera`) — saat ini validasi memakai `pytest` saja.
- Menambah sumber data baru ke `data/registry.json` (perlu keputusan cakupan).

## Perintah

```bash
make test | make integrity | make fetch | make rekonsiliasi | make backtest | make exports | make deploy
```
