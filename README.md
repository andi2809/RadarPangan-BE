# RadarPangan-Server

Backend **Radar Pangan** — FastAPI + pipeline data. Repo ini bagian dari 3 repo org `RadarPangan`
(Landing · Dashboard · **Server**).

Status: **kerangka MVP** (23 Okt 2026). Data di dalamnya **demo berlabel** — belum tersambung ke
PIHPS/pipeline sungguhan.

## Jalankan

```bash
uv venv .venv
uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/uvicorn app.main:app --reload --port 8000
```

- **Swagger UI (berisi contoh nilai):** http://localhost:8000/docs
- **Redoc:** http://localhost:8000/redoc
- **OpenAPI JSON:** http://localhost:8000/openapi.json

## Endpoint MVP (6)

| # | Endpoint | Keterangan |
|---|---|---|
| 1 | `GET /api/v1/publik/ringkasan-landing` | Agregat status + 5 wilayah sorotan |
| 2 | `GET /api/v1/komoditas` | 5 komoditas kanonik + acuan (`jenis_acuan`, `harga_acuan_rp`) |
| 3 | `GET /api/v1/wilayah` | 27 kab/kota Jawa Barat (kode Kemendagri + kode BPS) |
| 4 | `GET /api/v1/peta/status` | Choropleth status (`layer=aktual\|h7`) |
| 5 | `GET /api/v1/wilayah/{kode}/ringkasan` | Seri 14 hari + prakiraan H+7 (pita keyakinan) |
| 6 | `GET /api/v1/laporan-warga/sekitar` · `POST /api/v1/laporan-warga` | Verifikasi warga (klaster n dari 10) |

Tambahan: `GET /api/health`.

Semua respons memakai amplop `{ ok, data, meta }` dengan
`meta.tanggal_data`, `meta.mode_data` (`nyata|demo`), dan `meta.peringatan_kualitas`.

## Ekspor spec + fixtures (untuk FE)

```bash
.venv/bin/python scripts/export_openapi.py
```

Menghasilkan `openapi.json` (untuk `openapi-typescript` + lampiran proposal) dan
`fixtures/*.json` (contoh respons untuk membangun UI tanpa backend).

## Keputusan yang sudah dikunci (Andi, 23 Okt 2026)

| Hal | Keputusan |
|---|---|
| Beras | `beras_medium` |
| Minyak goreng | `minyakita` |
| PK wilayah | Kemendagri `NN.NN` (+ kolom `kode_bps`) |
| Target model | regresi harga absolut; gap ke acuan dilaporkan di `selisih_persen` |
| Daya beli | UMK Jawa Barat 2026 |
| Ambang status | `aman` ±5% · `waspada` +5…+10% · `kritis` >+10% · `turun` <-5% |
| Auth MVP | API key (`X-API-Key`), JWT menyusul |
| Nama file FDS | `WIA_FSDMIA2026_ini-nama-timnya-mau-apa.pdf` |

## Peringatan kejujuran data (jangan dihapus)

1. **HET/HAP di `app/data.py` masih ILUSTRATIF.** Harga pasar beras (Rp15.900/kg) memakai angka
   nyata PIHPS Jawa Barat 23 Okt 2026; angka acuan belum.
2. Setiap respons menandai `mode_data="demo"` + `peringatan_kualitas=["HET_ILUSTRATIF", ...]`.
3. Wilayah tanpa data **tidak diisi tebakan** — dikembalikan sebagai `status="tidak_ada_data"`.
4. Sebelum final: ganti angka acuan dengan Perbadan/regulasi resmi, dan pindahkan
   `mode_data` ke `"nyata"` hanya bila pipeline sudah menarik data resmi.

## Status data (23 Okt 2026)

✅ **Pipeline sudah menarik data nyata** dari PIHPS Bank Indonesia:
`data/raw/pihps_jabar_2026-10-20_2026-10-23.csv` — 144 baris (9 kab/kota × 4 komoditas × 4 hari).
Katalog & batasan lengkap: [`data/README.md`](data/README.md).

⚠️ **Dua temuan yang perlu keputusan:**
1. PIHPS hanya mencakup **9 dari 27** kab/kota Jawa Barat → 18 wilayah wajib tampil
   `tidak_ada_data` (tidak diimputasi).
2. PIHPS **tidak memisahkan Minyakita** (tersedia: curah, kemasan bermerk 1/2) →
   kode komoditas `minyakita` perlu diganti atau sumbernya dialihkan ke Bapanas.

## Selanjutnya

- Ganti `app/data.py` (data demo) dengan hasil pipeline → `mode_data="nyata"`
- Perhitungan status & skor EWS di SQL (satu sumber logika)
- Sumber kedua untuk menutup 18 kab/kota yang kosong (Bapanas saat pulih / SP2KP)

## Deploy ke Render (status: belum dilakukan)

Repo sudah ter-push (commit `8245709`, 23 Okt 2026). Tinggal 5 langkah di akun Render
**milik ketua/anggota** (tidak bisa dibuatkan orang lain):

1. Daftar di <https://render.com> → **Sign in with GitHub** (tidak perlu kartu kredit untuk Free).
2. Install **Render GitHub App** → beri akses ke organisasi `RadarPangan` dan repo
   `RadarPangan-Server` (repo masih privat, jadi akses ini wajib).
3. Dashboard Render → **New** → **Blueprint** → pilih `RadarPangan-Server`.
4. Render membaca `render.yaml` (runtime python, `uvicorn app.main:app --host 0.0.0.0 --port $PORT`,
   health check `/api/health`) → isi nilai `RADAR_API_KEY` saat diminta → **Apply**.
5. Tunggu build selesai, lalu verifikasi:
   `https://<nama-service>.onrender.com/docs` dan `/api/health`.

### Batas Free tier yang perlu diketahui

- **RAM 512 MB**, **spin-down setelah ±15 menit idle** → cold start **30–60 detik**.
- 750 jam instance/bulan (cukup untuk 1 service).
- Kalau region `singapore` ditolak, ganti ke `oregon` di `render.yaml`.

Karena spin-down itu, Dashboard **wajib** punya fallback ke `fixtures/*.json`
(atau snapshot statis) — jangan bergantung pada API saat juri membuka halaman pertama kali.

### Alternatif bila Render tidak jadi dipakai

| Opsi | Untuk apa | Catatan |
|---|---|---|
| **ngrok** (ide Andi) | Ekspos FastAPI lokal ke publik saat testing/mentoring | URL berubah tiap restart di free; VM harus selalu hidup; tidak disarankan untuk penjurian |
| Fly.io / Koyeb | Host proses Python | Perlu akun + kartu (Fly) |
| Vercel (Python runtime) | Bisa, tapi serverless | Cold start tiap request; lebih repot untuk FastAPI |
| **Supabase** | **Database** (Postgres), bukan tempat menjalankan FastAPI | Edge Functions = Deno, bukan Python |
| Netlify | **Situs statis** (Landing) | Tidak bisa menjalankan proses Python |
