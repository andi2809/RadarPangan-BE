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

## Selanjutnya

- Pipeline `ingest/` (PIHPS JSON → normalisasi → `harga_harian`)
- Perhitungan status & skor EWS di SQL (satu sumber logika)
- Ganti fixture dengan snapshot hasil pipeline

## Deploy (belum dilakukan — status 23 Okt 15:20)

**Belum live.** Repo ini masih lokal: belum di-push ke `RadarPangan/RadarPangan-Server`,
belum ada URL publik.

Langkah membuatnya live:

1. **Push** (dari mesin yang punya akses SSH):
   ```bash
   git init && git add . && git commit -m "feat: kerangka FastAPI + Swagger + fixtures"
   git branch -M main
   git remote add origin git@github.com:RadarPangan/RadarPangan-Server.git
   git push -u origin main
   ```
2. **Deploy ke Render** (gratis): Dashboard → *New* → **Blueprint** → pilih repo
   `RadarPangan-Server`. Blueprint `render.yaml` sudah disiapkan (runtime python,
   `uvicorn app.main:app --host 0.0.0.0 --port $PORT`, health check `/api/health`).
3. Set `RADAR_API_KEY` di Environment Render (jangan pernah commit nilainya).
4. Verifikasi: buka `https://<service>.onrender.com/docs` dan `/api/health`.

⚠️ Free tier Render **tidur setelah idle** (cold start ±30–60 detik). Karena itu
Dashboard wajib punya fallback ke `fixtures/*.json` — bukan sekadar nice-to-have.
