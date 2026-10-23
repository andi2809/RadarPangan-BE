"""Entry point Vercel (Python serverless) untuk Radar Pangan.

Vercel mendeteksi objek ASGI bernama `app` di file ini.
Routing diatur oleh `vercel.json` (semua path → /api/index).

Catatan: Vercel Python = serverless. Instance "dibekukan" saat idle lalu
dihidupkan lagi (cold start ±0,5–2 detik untuk FastAPI). Setelah hangat,
request berikutnya cepat. Batas durasi fungsi di Hobby = 10 detik — cukup
untuk endpoint JSON kita karena data dibaca dari snapshot lokal, bukan
memanggil portal pemerintah saat request.
"""

import sys
from pathlib import Path

# Pastikan paket lokal `app/` ikut ter-import saat runtime Vercel.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app  # noqa: E402,F401  (Vercel mencari variabel bernama `app`)
