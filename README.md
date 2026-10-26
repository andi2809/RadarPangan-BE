# RadarPangan-Server

Backend **Radar Pangan** — FastAPI + pipeline data. Repo ini bagian dari 3 repo org `RadarPangan`
(Dashboard · **Server**).

Status: **MVP berjalan di produksi** (26 Okt 2026) dengan data **nyata** PIHPS untuk 9 dari 27
kab/kota Jawa Barat; 18 wilayah sisanya ditampilkan `tidak_ada_data` (tidak diimputasi).


> ## ✅ STATUS: LIVE DI PRODUKSI (26 Okt 2026)
>
> **https://radar-pangan-server.vercel.app** · Swagger: [`/docs`](https://radar-pangan-server.vercel.app/docs)
>
> | Uji dari internet | Hasil |
> |---|---|
> | `/api/health`, `/docs`, `/openapi.json` | 200 |
> | `/api/v1/peta/status` | 27 wilayah — 9 berisi harga **nyata** (PIHPS), 18 `tidak_ada_data` |
> | `/api/v1/wilayah/32.75/ringkasan` | 200 — histori 14 hari + prakiraan H+7 |
> | CORS + preflight `POST` | `access-control-allow-origin: *` |
> | `POST /api/v1/laporan-warga` | 200 |
>
> **Kontrak untuk Front End:** [`docs/KONTRAK-FE.md`](docs/KONTRAK-FE.md)
> **Katalog data & cakupan:** [`data/README.md`](data/README.md)
>
> ⚠️ Dua hal yang belum ditutup: (1) `POST /laporan-warga` belum menolak tanpa
> `X-API-Key` dan belum ada rate-limit; (2) deploy dilakukan via **Vercel CLI**
> (upload folder), belum terhubung Git — jalankan `vercel --prod` untuk rilis berikutnya.

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
| Minyak goreng | `minyak_goreng_curah` (MVP) — PIHPS tidak memisahkan Minyakita |
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

## Deploy ke Vercel (rekomendasi — akun sudah ada)

FastAPI dijalankan sebagai **Python serverless function**: `api/index.py` mengekspor `app`,
dan `vercel.json` meneruskan semua path ke fungsi itu (region `sin1` = Singapura).

1. Buka <https://vercel.com/new> → import repo `RadarPangan-Server`
   (kalau repo privat, beri akses Vercel GitHub App ke org `RadarPangan`).
2. Framework preset: **Other**. Build command & output: biarkan kosong.
3. Environment Variables → tambahkan `RADAR_API_KEY`.
4. **Deploy** → URL `https://<project>.vercel.app`.
5. Verifikasi `/docs`, `/api/health`, `/api/v1/peta/status?komoditas=beras_medium`.

### Jalur cepat tanpa GitHub App (Vercel CLI)

Kalau import lewat dashboard meminta persetujuan GitHub App di org `RadarPangan`
(harus disetujui Andi), pakai CLI — ia meng-upload folder lokal, tidak menyentuh izin org:

```bash
cd ~/lomba/web-in-action-2026/radar-pangan-server
npx --yes vercel@latest login          # sekali saja (interaktif: email / GitHub)
npx --yes vercel@latest --prod         # deploy produksi dari folder ini
```

Saat diminta, pilih: *scope* akunmu, *link to existing project* → **No** (buat baru,
nama mis. `radar-pangan-api`), *directory* → `./`.
Setelah selesai, CLI mencetak URL produksi.

Tambahkan environment variable:

```bash
npx --yes vercel@latest env add RADAR_API_KEY production
npx --yes vercel@latest --prod          # redeploy agar env terpakai
```

`.vercelignore` sudah disiapkan agar `.venv/`, `data/`, `pipeline/`, dan `fixtures/`
tidak ikut ter-upload.

Batas Hobby yang relevan: **durasi fungsi 10 detik**, 1 GB RAM, dan cold start
±0,5–2 detik setelah idle (lebih lambat dari Node karena interpreter Python + import
FastAPI/Pydantic). Setelah instance hangat, request berikutnya cepat — bukan "tiap request".

## Deploy ke Hugging Face Spaces (Docker = berbayar; Gradio = gratis 2 Space)

Prasyarat sekali saja di browser:
1. Daftar di <https://huggingface.co> (tidak perlu kartu).
2. **New → Space** → **SDK: Docker** → **Visibility: Public** → nama `radar-pangan-api`.
3. Buat **Write token**: <https://huggingface.co/settings/tokens>.

Lalu dari mesin ini:

```bash
export HF_TOKEN=hf_xxxxxxxxxxxxxxxx
./deploy/hf_push.sh <username>/radar-pangan-api
```

Script `deploy/hf_push.sh` menyalin `app/`, `requirements.txt`, `Dockerfile`, lalu menulis
`README.md` Space dengan metadata Docker (`app_port: 7860`) dan mendorongnya.
Build otomatis; URL biasanya `https://<username>-radar-pangan-api.hf.space`.

- Swagger: `/docs` · Health: `/api/health`
- Secret: **Space Settings → Variables and secrets** → tambahkan `RADAR_API_KEY`
- Free tier: 2 vCPU / 16 GB, **tidur setelah 48 jam idle**, storage ephemeral.

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
