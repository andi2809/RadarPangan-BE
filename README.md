# RadarPangan-Server

Backend **Radar Pangan** — API *early warning & decision support* harga pangan pokok Jawa Barat.
FastAPI, dideploy di Vercel. Repo ini bagian dari organisasi `RadarPangan` (Dashboard · **Server**).

**Produksi:** https://radar-pangan-server.vercel.app · Swagger: [`/docs`](https://radar-pangan-server.vercel.app/docs)

---

## Dokumen

- `docs/RUMUS_DAN_PERHITUNGAN.md` — semua rumus & perhitungan dalam bahasa manusia
  (PDF: `dokumen/RUMUS_RADAR_PANGAN.pdf`)
- `data/PROTOKOL.md` — aturan pipeline, provenance, dan catatan metodologi
- `docs/KONTRAK-FE.md` — kontrak endpoint untuk front end

## Data historis

Sumber utama: **Bapanas 189.812 baris (27 kab/kota, 2024–2026)**. Tidak ada sumber harga pembanding; pembanding hanya HET/HAP dan laporan warga.
Bundel Vercel hanya memuat `data/raw`, `data/referensi`, dan `data/derived/*.json` —
CSV turunan (6–7 MB) tidak ikut. Rincian: `data/README.md` bagian 8.

## Status

| | |
|---|---|
| Versi | MVP — target First Draft Submission 1 Nov 2026 |
| Data | **nyata** — dataset resmi Badan Pangan Nasional, 1 Jan 2024 – 31 Okt 2026 |
| Cakupan | **9 dari 27** kab/kota (batas sumber, bukan bug) |
| Komoditas | 5 — beras medium, cabai rawit merah, bawang merah, telur ayam ras, minyak goreng curah |
| Uji | **18 tes** `pytest`, termasuk integritas data & determinisme |
| Deploy | Vercel (region `sin1`) lewat CLI |

---

## Jalankan lokal

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --reload --port 8000
# Swagger http://localhost:8000/docs · OpenAPI /openapi.json
```

Perintah operasional ada di `Makefile`:

```bash
make test        # seluruh uji              make backtest      # backtest ambang EWS
make integrity   # uji integritas data      make exports       # openapi.json + fixtures
make fetch START=2026-10-26 END=2026-10-26  make deploy        # Vercel produksi
```

---

## Endpoint

Amplop respons seragam `{ ok, data, meta }`. `meta` selalu memuat `tanggal_data`, `sumber`,
`mode_data` (`nyata|demo|simulasi`), dan `peringatan_kualitas`.

| Metode | Path | Isi |
|---|---|---|
| GET | `/api/health` | status layanan |
| GET | `/api/v1/komoditas` | 5 komoditas + acuan (HET/HAP) |
| GET | `/api/v1/wilayah` | 27 kab/kota (kode Kemendagri + BPS) |
| GET | `/api/v1/wilayah/{kode}/ringkasan` | detail wilayah + histori 14 hari + prakiraan H+7 |
| GET | `/api/v1/laporan-warga/sekitar` | laporan warga di sekitar titik (kosong sampai ada kiriman nyata) |
| POST | `/api/v1/laporan-warga` | kirim laporan warga |
| GET | `/api/v1/publik/ringkasan-landing` | ringkasan landing, dihitung dari data nyata |
| GET | `/api/v1/meta/sumber` | registry sumber + run terakhir + kesegaran |
| GET | `/api/v1/meta/backtest` | hasil backtest ambang EWS |
| GET | `/api/v1/meta/disparitas` | sebaran harga antarwilayah per hari (Bapanas) |
| GET | `/openapi.json` · `/docs` | skema & Swagger UI |

Kontrak untuk front end: [`docs/KONTRAK-FE.md`](docs/KONTRAK-FE.md).

---

## Data

- **Sumber tunggal:** dataset resmi Badan Pangan Nasional (surat No. 1014/TS.02.03/B.2/11/2026),
  diimpor `pipeline/bapanas_import.py` → `data/paket/bapanas.csv.gz` (189.812 baris, 27 kab/kota,
  6 komoditas, harian 1 Jan 2024 – 31 Okt 2026).
- **Pembanding yang sah:** acuan pemerintah HET/HAP (tabel `data/referensi/het_hap.csv`) dan
  laporan warga sebagai data riil hari ini. Tidak ada sumber harga pembanding lain.
  `/statistik/area` punya
  data per kab/kota + Minyakita, tetapi hanya bisa diakses lewat **ekspor manual** (bukan REST).
- **Registry sumber:** [`data/registry.json`](data/registry.json) — tier, granularitas, akses, cakupan.
- **Jejak tarikan (lineage):** `data/derived/runs.jsonl` — `run_id`, status, jumlah baris, `sha256`.
- **Protokol pengukuran:** [`data/PROTOKOL.md`](data/PROTOKOL.md) — definisi "harga" per sumber,
  bias terukur, aturan agregasi.
- **Katalog & temuan data:** [`data/README.md`](data/README.md).

### Batasan yang wajib disebut saat presentasi

1. Cakupan **9/27** kab/kota; 7 kota + 2 kabupaten (**urban skew**).
2. 61 dari 85 hari kalender berisi data — **24 hari kosong, semuanya Sabtu–Minggu**.
3. Wilayah tanpa data dikembalikan `tidak_ada_data` — **tidak diimputasi**.
4. Acuan HET/HAP ada di `data/referensi/het_hap.csv` dan `app/routers/peta.py`; label
   **Minyakita vs Minyak Goreng Curah masih menunggu keputusan tim**.

---

## Metodologi & validasi

| Berkas | Isi |
|---|---|
| `pipeline/disparitas.py` → `data/derived/disparitas.json` | sebaran harga antarwilayah per hari (sinyal alternatif) |
| `app/services/skor.py` | satu sumber skor EWS (peta + detail) |
| `app/services/prakiraan.py` | **naive** + pita kuantil empiris untuk H+7 |
| `pipeline/pita_prakiraan.py` | kalibrasi pita dari arsip mentah (`make pita`) |
| `pipeline/benchmark_ews.py` | benchmark model (naive/SES/Holt/HW) pada data Bapanas |
| `pipeline/bapanas_import.py` | impor Excel Bapanas → `data/paket/bapanas.csv.gz` (sumber utama EWS) |
| [`docs/HASIL_BACKTEST_EWS.md`](docs/HASIL_BACKTEST_EWS.md) | laporan naratif + tabel hasil |
| [`docs/STRATEGI_SUMBER_DATA.md`](docs/STRATEGI_SUMBER_DATA.md) | strategi federasi sumber + lineage |
| [`docs/KESIMPULAN_METODOLOGI.md`](docs/KESIMPULAN_METODOLOGI.md) | kesimpulan metodologi + lima perubahan implementasi |

Setiap baris `/peta/status` kini membawa `sumber`, `jenis_harga` (`pasar`|`acuan`), dan `flat_days`:

Ringkasan temuan (26 Okt 2026): status "kritis" mengukur **kepatuhan HET**, bukan sinyal dini —
beras & minyak nyaris selalu di atas HET sehingga tidak informatif; cabai informatif (presisi 61%,
recall 93%, jeda 6 hari). Sinyal momentum: F1 ≈ 43 pada ambang 1%.

---

## Uji

```bash
.venv/bin/python -m pytest -q      # 18 lulus
```

`tests/test_data_integrity.py` menjaga: harga positif & numerik, kunci natural unik per snapshot
**dan** setelah penggabungan, tanggal tidak di masa depan, wilayah/komoditas dikenal, pemuatan ulang
deterministik, serta invarian `/peta/status` (27 item; harga `null` ⇔ `tidak_ada_data`).

---

## Deploy

```bash
npx --yes vercel@latest --prod --yes     # atau: make deploy
```

Tiga jebakan yang pernah terjadi:

1. `vercel.json` → `includeFiles` **wajib** `"{app,data}/**"`. Tanpa `data/`, API kosong.
2. **Jangan** menambahkan `rewrites` — Vercel mendeteksi FastAPI dan menyajikan app di root;
   rewrite ke `/api/index` membuat semua rute 404.
3. Deploy memakai **CLI** (upload folder), belum terhubung Git.

---

## Struktur repo

```
app/            FastAPI — routers, schemas, services/harga.py
api/index.py    entrypoint Vercel
pipeline/       bapanas_import · pita_prakiraan · integritas_bapanas · disparitas · evaluasi_model · runlog
data/           raw snapshot · referensi · derived · registry.json · PROTOKOL.md
docs/           KONTRAK-FE.md
scripts/        export_openapi.py
tests/          pytest (API + integritas data)
fixtures/       contoh respons untuk fallback front end
Makefile        perintah operasional
```

---

## Aturan dokumentasi (wajib)

Setiap commit yang mengubah **perilaku** — endpoint, field respons, sumber data, ambang, atau cara
menjalankan — **wajib** memperbarui:

1. `README.md` (tabel endpoint/status/data yang terdampak),
2. `docs/KONTRAK-FE.md` bila menyentuh bentuk respons,
3. `data/PROTOKOL.md` bila menyentuh definisi atau asal data.

Commit tanpa pembaruan dokumentasi dianggap **belum selesai**.
