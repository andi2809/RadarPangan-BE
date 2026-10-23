#!/usr/bin/env bash
# Dorong RadarPangan-Server ke Hugging Face Spaces (Docker SDK).
#
# Prasyarat (sekali saja, di browser):
#   1. Daftar di https://huggingface.co (tanpa kartu)
#   2. New → Space → SDK: Docker → Visibility: Public → nama mis. "radar-pangan-api"
#   3. Buat Write token: https://huggingface.co/settings/tokens
#
# Pakai:
#   export HF_TOKEN=hf_xxxxxxxxxxxxxxxx
#   ./deploy/hf_push.sh <username>/<nama-space>
#
# Contoh:
#   ./deploy/hf_push.sh caerdfasgrae/radar-pangan-api

set -euo pipefail

SPACE="${1:?pakai: ./deploy/hf_push.sh <username>/<nama-space>}"
: "${HF_TOKEN:?set HF_TOKEN dulu (write token dari https://huggingface.co/settings/tokens)}"

AKAR="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "→ clone Space ${SPACE}"
git clone --quiet "https://user:${HF_TOKEN}@huggingface.co/spaces/${SPACE}" "$TMP/space"

# Bersihkan isi lama (kecuali .git), lalu salin artefak yang dibutuhkan container.
find "$TMP/space" -mindepth 1 -maxdepth 1 -not -name '.git' -exec rm -rf {} +
cp -r "$AKAR/app" "$AKAR/requirements.txt" "$AKAR/Dockerfile" "$TMP/space/"

cat > "$TMP/space/README.md" <<'EOF'
---
title: Radar Pangan API
emoji: 🌾
colorFrom: green
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

API FastAPI **Radar Pangan** (MVP MIA 2026).

- Swagger: `/docs`
- Health: `/api/health`
- Data: PIHPS Bank Indonesia — demo berlabel (`meta.mode_data`)
EOF

cd "$TMP/space"
git add -A
git -c user.name="Abyan" -c user.email="abyannz2003@gmail.com" \
    commit --quiet -m "deploy: Radar Pangan API (Docker, port 7860)"
git push --quiet

echo "✅ terkirim. Build berjalan otomatis di Hugging Face."
echo "   Lihat log & URL di: https://huggingface.co/spaces/${SPACE}"
echo "   URL aplikasi biasanya: https://$(echo "${SPACE}" | tr '/' '-').hf.space"
