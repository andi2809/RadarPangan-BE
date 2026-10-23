# Image portabel untuk RadarPangan-Server (FastAPI).
# Dipakai bila host meminta Docker: Render (opsional), Hugging Face Spaces, Fly, Koyeb.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=7860

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 7860

# $PORT diisi otomatis oleh host (Render) atau 7860 (Hugging Face Spaces).
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-7860}"]
