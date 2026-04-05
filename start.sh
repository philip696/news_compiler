#!/bin/bash
# Railway startup script for GEB backend

set -e  # Exit on error

echo "🚀 GEB Backend Startup Script"
echo "Port: ${PORT:-8000}"
echo "Host: 0.0.0.0"

# Change to backend directory
cd backend

# Run uvicorn with proper port handling
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port ${PORT:-8000} \
    --timeout-keep-alive 5 \
    --access-log
