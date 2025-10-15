#!/usr/bin/env bash
set -euo pipefail

echo "Waiting for database ${DB_HOST:-postgres}:${DB_PORT:-5432}..."
for i in {1..60}; do
  if nc -z "${DB_HOST:-postgres}" "${DB_PORT:-5432}" >/dev/null 2>&1; then
    echo "Database is up!"
    break
  fi
  echo "(attempt $i) DB not ready yet..."
  sleep 2
done

echo "Applying database migrations..."
alembic upgrade head

echo "Starting API server..."
exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

