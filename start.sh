#!/bin/bash
# Railway startup script for GEB backend

set -e  # Exit on error

echo "🚀 GEB Backend Startup"
echo "Port: ${PORT:-8000}"
echo "Host: 0.0.0.0"
echo "Working directory: $(pwd)"

# App code is already in /app (from Dockerfile COPY backend/ .)
# No need to cd - just run uvicorn from current directory

exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port ${PORT:-8000} \
    --timeout-keep-alive 5 \
    --access-log
