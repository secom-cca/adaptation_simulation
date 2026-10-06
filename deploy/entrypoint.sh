#!/bin/sh
set -eu

WORKERS="${UVICORN_WORKERS:-2}"

# Ensure writable data dirs (EFS or local volume)
mkdir -p /app/backend/data/operation_logs

echo "Starting nginx..."
nginx

echo "Starting uvicorn (workers=${WORKERS})..."
cd /app/backend
exec uvicorn main:app --host 127.0.0.1 --port 8000 --workers "${WORKERS}"
