okay"""
Rate Limiting Tests for WeChat API Endpoints

Run these tests to verify rate limits are working correctly:
    python -m pytest backend/tests/test_wechat_rate_limiting.py -v

Requires valid JWT token in environment variable: TEST_JWT_TOKEN
"""

import pytest
import asyncio
import httpx
from datetime import datetime
import os


class TestWeChatRateLimiting:
    """Test rate limiting on WeChat API endpoints"""
    
    BASE_URL = "http://localhost:8000"
    
    @pytest.fixture
    def jwt_token(self):
        """Get JWT token from environment"""
        token = os.getenv("TEST_JWT_TOKEN")
        if not token:
            pytest.skip("TEST_JWT_TOKEN environment variable not set")
        return token
    
    @pytest.fixture
    def headers(self, jwt_token):
        """Standard headers with authentication"""
        return {"Authorization": f"Bearer {jwt_token}"}
    
    @pytest.fixture
    async def client(self):
        """Async HTTP client"""
        async with httpx.AsyncClient(base_url=self.BASE_URL) as client:
            yield client
    
    # ===== Auth Endpoints =====
    
    @pytest.mark.asyncio
    async def test_logout_rate_limit_5_per_minute(self, client, headers):
        """Test POST /api/wechat/auth/logout → 5/minute"""
        endpoint = "/api/wechat/auth/logout"
        limit = 5
        
        successful = 0
        rate_limited = 0
        
        # Make requests rapidly
        for i in range(limit + 2):  # Try 2 more than limit
            response = await client.post(endpoint, headers=headers)
            
            if response.status_code == 200:
                successful += 1
                print(f"Request {i+1}: 200 OK")
            elif response.status_code == 429:
                rate_limited += 1
                print(f"Request {i+1}: 429 Rate Limited")
                error_data = response.json()
                assert error_data["error"] == "RATE_LIMIT_EXCEEDED"
                print(f"  Detail: {error_data['detail']}")
        
        # Verify rate limit triggered
        assert successful == limit, f"Expected {limit} successful requests, got {successful}"
        assert rate_limited == 2, f"Expected 2 rate-limited responses, got {rate_limited}"
    
    # ===== Account Endpoints =====
    
    @pytest.mark.asyncio
    async def test_subscribe_rate_limit_5_per_minute(self, client, headers):
        """Test POST /api/wechat/accounts → 5/minute"""
        endpoint = "/api/wechat/accounts"
        limit = 5
        
        rate_limited = 0
        
        # Note: This test will make 5 subscribe attempts, may fail on duplicates
        # That's OK - we're testing the rate limit, not subscribe logic
        for i in range(limit + 1):
            response = await client.post(endpoint, headers=headers, json={"account_id": 1})
            
            if response.status_code == 429:
                rate_limited += 1
                print(f"Request {i+1}: 429 Rate Limited (as expected)")
            else:
                print(f"Request {i+1}: {response.status_code}")
        
        assert rate_limited > 0, "Expected rate limit to be triggered"
    
    @pytest.mark.asyncio
    async def test_list_accounts_rate_limit_10_per_minute(self, client, headers):
        """Test GET /api/wechat/accounts → 10/minute"""
        endpoint = "/api/wechat/accounts"
        limit = 10
        
        successful = 0
        rate_limited = 0
        
        # Make 12 requests (10 allowed + 2 over limit)
        for i in range(limit + 2):
            response = await client.get(endpoint, headers=headers)
            
            if response.status_code == 200:
                successful += 1
                # print(f"Request {i+1}: 200 OK")
            elif response.status_code == 429:
                rate_limited += 1
                print(f"Request {i+1}: 429 Rate Limited")
        
        print(f"Successful: {successful}, Rate Limited: {rate_limited}")
        # Rate limit should trigger at some point
        assert rate_limited > 0, "Expected some rate-limited responses"
    
    @pytest.mark.asyncio
    async def test_delete_account_rate_limit_10_per_minute(self, client, headers):
        """Test DELETE /api/wechat/accounts/{id} → 10/minute"""
        endpoint = "/api/wechat/accounts/1"
        
        response = await client.delete(endpoint, headers=headers)
        # First request should succeed (or fail with auth error, but not 429)
        assert response.status_code != 429, "First request should not be rate limited"
        print(f"First DELETE: {response.status_code}")
    
    @pytest.mark.asyncio
    async def test_mute_account_rate_limit_20_per_minute(self, client, headers):
        """Test POST /api/wechat/accounts/{id}/mute → 20/minute"""
        endpoint = "/api/wechat/accounts/1/mute"
        
        response = await client.post(endpoint, headers=headers)
        print(f"Mute request: {response.status_code}")
        # First request should not be rate limited
        assert response.status_code != 429, "First request should not be rate limited"
    
    @pytest.mark.asyncio
    async def test_unmute_account_rate_limit_20_per_minute(self, client, headers):
        """Test POST /api/wechat/accounts/{id}/unmute → 20/minute"""
        endpoint = "/api/wechat/accounts/1/unmute"
        
        response = await client.post(endpoint, headers=headers)
        print(f"Unmute request: {response.status_code}")
        # First request should not be rate limited
        assert response.status_code != 429, "First request should not be rate limited"
    
    # ===== Article Endpoints =====
    
    @pytest.mark.asyncio
    async def test_list_articles_rate_limit_30_per_minute(self, client, headers):
        """Test GET /api/wechat/articles → 30/minute"""
        endpoint = "/api/wechat/articles"
        
        responses = []
        for i in range(3):  # Just test a few
            response = await client.get(endpoint, headers=headers)
            responses.append(response.status_code)
            # print(f"Request {i+1}: {response.status_code}")
        
        # With generous limit (30/min), even 3 requests should succeed
        success_count = sum(1 for status in responses if status == 200)
        print(f"List articles: {success_count}/3 successful")
        assert success_count > 0, "At least some list requests should succeed"
    
    @pytest.mark.asyncio
    async def test_get_article_rate_limit_30_per_minute(self, client, headers):
        """Test GET /api/wechat/articles/{id} → 30/minute"""
        endpoint = "/api/wechat/articles/1"
        
        response = await client.get(endpoint, headers=headers)
        print(f"Get article: {response.status_code}")
        # First request should not be rate limited
        assert response.status_code != 429, "First request should not be rate limited"
    
    # ===== Rate Limit Response Format =====
    
    @pytest.mark.asyncio
    async def test_rate_limit_response_format(self, client, headers):
        """Verify rate limit responses have correct format"""
        endpoint = "/api/wechat/auth/logout"
        
        # Make enough requests to trigger rate limit
        for i in range(7):
            response = await client.post(endpoint, headers=headers)
            if response.status_code == 429:
                data = response.json()
                
                # Verify response structure
                assert "error" in data, "Rate limit response missing 'error' field"
                assert "detail" in data, "Rate limit response missing 'detail' field"
                
                # Verify error code
                assert data["error"] == "RATE_LIMIT_EXCEEDED"
                assert "too many requests" in data["detail"].lower()
                
                print(f"Rate limit response: {data}")
                return
        
        pytest.fail("Rate limit was never triggered")


class TestRateLimitingIntegration:
    """Integration tests for rate limiting behavior"""
    
    @pytest.mark.asyncio
    async def test_rate_limit_resets_after_time(self):
        """Verify rate limits reset after time window expires"""
        # This is a placeholder - in real env would need timed test
        pytest.skip("Requires time-based test setup (>1 minute wall clock)")
    
    @pytest.mark.asyncio
    async def test_rate_limit_per_ip_address(self):
        """Verify rate limits are per IP address"""
        # Different clients should have separate limits
        pytest.skip("Requires multi-client test setup")
    
    @pytest.mark.asyncio
    async def test_rate_limit_respects_redis(self):
        """Verify limits persist across requests"""
        pytest.skip("Requires Redis verification")


# ===== Manual Testing Commands =====

class ManualTestingGuide:
    """
    Run these commands for manual testing:
    
    # Set your JWT token
    export TEST_JWT_TOKEN="your_jwt_token_here"
    
    # Run all rate limiting tests
    pytest backend/tests/test_wechat_rate_limiting.py -v
    
    # Run specific test
    pytest backend/tests/test_wechat_rate_limiting.py::TestWeChatRateLimiting::test_logout_rate_limit_5_per_minute -v -s
    
    # Run with live output
    pytest backend/tests/test_wechat_rate_limiting.py -v -s
    
    # Using curl - test logout endpoint (5/min limit)
    TOKEN="your_token"
    for i in {1..6}; do
        echo "Request $i:"
        curl -X POST http://localhost:8000/api/wechat/auth/logout \\
            -H "Authorization: Bearer $TOKEN" \\
            -H "Content-Type: application/json" \\
            -w "\\nStatus: %{http_code}\\n\\n"
    done
    
    # Using curl - test list accounts (10/min limit)
    TOKEN="your_token"
    for i in {1..12}; do
        curl -X GET http://localhost:8000/api/wechat/accounts \\
            -H "Authorization: Bearer $TOKEN" \\
            -w "Request $i: %{http_code}\\n"
    done
    """
    pass


if __name__ == "__main__":
    print(ManualTestingGuide.__doc__)
