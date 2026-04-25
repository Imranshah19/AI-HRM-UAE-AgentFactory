# ══════════════════════════════════════════════════════════════════════════════
# AI-HRMS — Backend Dockerfile (FastAPI)
# Multi-stage: development (hot-reload) + production (optimized)
# ══════════════════════════════════════════════════════════════════════════════

# ─── Base ─────────────────────────────────────────────────────────────────────
# WINDOWS DNS FIX: If Docker cannot pull python:3.11-slim, run:
#   docker pull python:3.11-slim
# Or override the image via build arg:
#   docker-compose build --build-arg PYTHON_IMAGE=python:3.11-slim
# Mirror alternative: set PYTHON_IMAGE=mirror.gcr.io/library/python:3.11-slim
ARG PYTHON_IMAGE=python:3.11-slim
FROM ${PYTHON_IMAGE} AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies (no build-essential: all Python packages use pre-built wheels)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libmagic1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ─── Dependencies ─────────────────────────────────────────────────────────────
FROM base AS dependencies

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# ─── Development ──────────────────────────────────────────────────────────────
FROM dependencies AS development

# Dev has full source mounted as volume — no COPY needed
# Uvicorn --reload watches /app for file changes

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ─── Production ───────────────────────────────────────────────────────────────
FROM dependencies AS production

COPY . .

# Create non-root user for security
RUN addgroup --system --gid 1001 appgroup && \
    adduser  --system --uid 1001 --ingroup appgroup appuser && \
    mkdir -p /uploads && chown -R appuser:appgroup /uploads /app

USER appuser

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", \
     "--workers", "4", "--proxy-headers", "--forwarded-allow-ips", "*"]
