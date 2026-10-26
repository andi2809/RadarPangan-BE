"""Radar Pangan API — FastAPI (MVP 1 Nov 2026).

Layanan Backend & GIS Early Warning and Decision Support System (EWS & DSS)
untuk pemantauan disparitas harga pangan pokok se-Jawa Barat (27 Kab/Kota).
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import publik, komoditas, wilayah, peta, laporan, ai_advisor, meta

app = FastAPI(
    title="Radar Pangan API — Early Warning & Decision Support System",
    description=(
        "API MVP Radar Pangan — GIS early warning + decision support harga pangan "
        "Jawa Barat (27 kab/kota, 5 komoditas poko).\n\n"
        "Mendukung integrasi 100% dengan Front End Dashboard MapLibre dan Landing Page."
    ),
    version="1.0.0",
)

# CORS configuration for Front End consumption (Vercel, Netlify, Localhost)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "https://radar-pangan.netlify.app",
        "https://radar-pangan-dashboard.netlify.app",
        "*"
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Mount Modular Routers
app.include_router(publik.router)
app.include_router(komoditas.router)
app.include_router(wilayah.router)
app.include_router(peta.router)
app.include_router(laporan.router)
app.include_router(meta.router)
app.include_router(ai_advisor.router)


@app.get("/api/health", tags=["Sistem"], summary="Health check")
def health() -> dict:
    return {
        "status": "healthy",
        "service": "radar-pangan-server",
        "version": app.version,
        "active_regions": 27,
        "engine": "FastAPI + Google Antigravity SDK Agent",
    }


@app.get("/", tags=["Sistem"])
def root() -> dict:
    return {
        "message": "Radar Pangan API is running. Visit /docs for Swagger UI OpenAPI documentation."
    }
