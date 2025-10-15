# syntax=docker/dockerfile:1

FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps for common Python wheels (psycopg2, cryptography, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    netcat-openbsd \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files first for better caching
COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Ensure entrypoint is executable
RUN chmod +x docker/entrypoint.sh || true

EXPOSE 8000

# Default command (can be overridden by compose)
CMD ["/bin/bash", "docker/entrypoint.sh"]
