#!/bin/bash

# Webhose Synergy Quick Start Guide
# Run this to integrate your first Webhose dataset

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║     WEBHOSE + SYNERGY INTEGRATION - QUICK START GUIDE           ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

cd /Users/philipdewanto/Downloads/Code/GEB

echo "✓ Your Synergy app is ready for Webhose datasets"
echo ""
echo "WHAT'S BEEN SET UP:"
echo "  • Backend integrates Webhose JSON files automatically"
echo "  • Cloned free-news-datasets repository to: free-news-datasets/"
echo "  • Created webhose_extended/ folder for manual uploads"
echo ""

echo "STEP 1: Download a Webhose Dataset"
echo "  1. Go to: https://github.com/Webhose/free-news-datasets"
echo "  2. Click: News_Datasets folder"
echo "  3. Select a file (e.g., finance_20250101.json or just browse)"
echo "  4. Click: Download button"
echo ""

echo "STEP 2: Save to Synergy"
echo "  • Save to: backend/data/webhose_extended/"
echo "  • Example:"
echo "    cp ~/Downloads/finance_20250101.json backend/data/webhose_extended/"
echo ""

echo "STEP 3: Restart Backend"
echo "  • Run these commands:"
echo ""
echo "    lsof -i :8007 | grep -v COMMAND | awk '{print \$2}' | xargs kill -9"
echo "    sleep 2"
echo "    cd backend"
echo "    python -m uvicorn app.main:app --host 127.0.0.1 --port 8007"
echo ""

echo "STEP 4: Done!"
echo "  • The Webhose articles will load automatically"
echo "  • Go to http://localhost:3000"
echo "  • Login with: demo@example.com / secret123"
echo "  • You should see many more articles in the feed!"
echo ""

echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "CHECK PROGRESS:"
echo "  curl http://127.0.0.1:8007/healthz | jq .articles"
echo ""

echo "AVAILABLE DATASETS:"
echo "  • Financial news (finance_*.json)"
echo "  • Technology (tech_*.json)"
echo "  • Politics (politics_*.json)"
echo "  • Sports (sports_*.json)"
echo "  • Climate (climate_*.json)"
echo "  • Health (health_*.json)"
echo "  • And many more!"
echo ""

echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "CURRENT STATUS:"
echo ""

# Check current article count
ARTICLES=$(curl -s http://127.0.0.1:8007/healthz 2>/dev/null | grep -o '"articles": [0-9]*' | grep -o '[0-9]*' || echo "unknown")
echo "  Articles in Synergy: $ARTICLES"
echo "  Backend running: $([ $(lsof -i :8007 | wc -l) -gt 1 ] && echo 'YES ✓' || echo 'NO')"
echo "  Frontend running: $([ $(lsof -i :3000 | wc -l) -gt 1 ] && echo 'YES ✓' || echo 'NO')"
echo ""

echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "NEXT STEPS:"
echo "  1. Download 1-2 datasets to test"
echo "  2. Add more datasets for comprehensive coverage"  
echo "  3. Check that personalization works by following topics"
echo "  4. Bookmark and like articles"
echo "  5. View your profile for saved content"
echo ""

echo "Questions? See:"
echo "  • WEBHOSE_SYNERGY_INTEGRATION.md (detailed docs)"
echo "  • WEBHOSE_INTEGRATION_GUIDE.md (setup guide)"
echo ""
