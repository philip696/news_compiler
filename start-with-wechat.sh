#!/bin/bash
# Quick start script for GEB with wewe-rss integration

set -e

echo "🚀 Starting GEB with WeChat Integration..."

# Check if .env exists
if [ ! -f backend/.env ]; then
    echo "📝 Creating .env file from .env.example..."
    cp backend/.env.example backend/.env
    echo "⚠️  Please update backend/.env with your configuration"
fi

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -r backend/requirements.txt

# Start services with Docker Compose
echo "🐳 Starting Docker services (wewe-rss)..."
docker-compose up -d wewe-rss fastapi

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 5

echo ""
echo "✅ GEB and wewe-rss are running!"
echo ""
echo "🌐 Access:"
echo "   - FastAPI backend: http://localhost:8000"
echo "   - FastAPI docs: http://localhost:8000/docs"
echo "   - wewe-rss: http://localhost:4000"
echo ""
echo "📚 WeChat API Endpoints:"
echo "   - GET /api/wechat/articles - Get all articles"
echo "   - GET /api/wechat/accounts/{id}/articles - Get account articles"
echo "   - POST /api/wechat/accounts/{id}/update - Trigger manual update"
echo "   - GET /api/wechat/rss/{id} - Get as RSS feed"
echo "   - GET /api/wechat/atom/{id} - Get as Atom feed"
echo "   - GET /api/wechat/health - Check health status"
echo ""
echo "📖 Full API docs at: http://localhost:8000/docs"
