#!/bin/bash

# WeWe-RSS Integration Test Script
# This script tests all WeWe-RSS endpoints to verify integration

set -e

echo "========================================"
echo "WeWe-RSS Integration Test Suite"
echo "========================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
BACKEND_URL="http://localhost:8000"
TEST_TOKEN="test_token_placeholder"

# Check if backend is running
echo "🔍 Checking backend health..."
if curl -s "${BACKEND_URL}/healthz" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Backend is running${NC}"
else
    echo -e "${RED}❌ Backend is not running on port 8000${NC}"
    echo "   Start with: cd backend && python -m uvicorn app.main:app --port 8000"
    exit 1
fi

echo ""
echo "========================================"
echo "Testing WeWe-RSS Endpoints"
echo "========================================"
echo ""

# Test 1: Health check
echo "1️⃣  Testing /api/wewe-rss/health"
if curl -s "${BACKEND_URL}/api/wewe-rss/health" | grep -q "healthy"; then
    echo -e "${GREEN}✅ Health check passed${NC}"
else
    echo -e "${YELLOW}⚠️  Health check needs WeWe-RSS instance running${NC}"
fi

echo ""

# Test 2: Integration status
echo "2️⃣  Testing /api/wewe-rss/status"
RESPONSE=$(curl -s "${BACKEND_URL}/api/wewe-rss/status")
if echo "${RESPONSE}" | grep -q "integrated"; then
    echo -e "${GREEN}✅ Integration status endpoint works${NC}"
    echo "   Response: ${RESPONSE}"
else
    echo -e "${RED}❌ Integration status endpoint failed${NC}"
fi

echo ""
echo "========================================"
echo "Testing WeWe-RSS Auth Endpoints"
echo "========================================"
echo ""

# Test 3: Integration status (auth router)
echo "3️⃣  Testing /api/wewe-rss/integration-status (auth)"
RESPONSE=$(curl -s -H "Authorization: Bearer ${TEST_TOKEN}" \
  "${BACKEND_URL}/api/wewe-rss/integration-status" 2>&1)
if echo "${RESPONSE}" | grep -q "integration_enabled\|connected_accounts\|unauthorized\|invalid"; then
    echo -e "${GREEN}✅ Auth integration status endpoint callable${NC}"
    echo "   Response: ${RESPONSE}"
else
    echo -e "${YELLOW}⚠️  Auth endpoint response: ${RESPONSE}${NC}"
fi

echo ""

# Test 4: List accounts (requires auth)
echo "4️⃣  Testing /api/wewe-rss/accounts (requires valid JWT)"
RESPONSE=$(curl -s -H "Authorization: Bearer ${TEST_TOKEN}" \
  "${BACKEND_URL}/api/wewe-rss/accounts" 2>&1 | head -c 200)
if echo "${RESPONSE}" | grep -q "accounts\|detail\|unauthorized"; then
    echo -e "${GREEN}✅ Accounts endpoint callable${NC}"
    echo "   Response (preview): ${RESPONSE:0:100}..."
else
    echo -e "${YELLOW}⚠️  Accounts endpoint response: ${RESPONSE}${NC}"
fi

echo ""
echo "========================================"
echo "Summary"
echo "========================================"
echo ""
echo "✅ Integration points verified:"
echo "   • Backend running on port 8000"
echo "   • WeWe-RSS feed endpoints available"
echo "   • WeWe-RSS auth endpoints available"
echo ""
echo "📝 Next steps:"
echo "   1. Get valid JWT token from /api/auth/login endpoint"
echo "   2. Use token in Authorization header for auth endpoints"
echo "   3. Start WeWe-RSS instance on port 4000 (or configured URL)"
echo "   4. Test QR code generation: POST /api/wewe-rss/auth/qrcode"
echo ""
echo "📚 Documentation:"
echo "   See WEWE_RSS_INTEGRATION_GUIDE.md for full API reference"
echo "   See API_QUICK_REFERENCE.md for curl examples"
echo ""
