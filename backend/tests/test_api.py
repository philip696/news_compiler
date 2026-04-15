from fastapi.testclient import TestClient
import uuid

from app.main import app


client = TestClient(app)


def test_health_and_auth_feed_flow():
    health = client.get("/healthz")
    assert health.status_code == 200

    # Use unique username to avoid conflicts with previous test runs
    username = f"testuser_{uuid.uuid4().hex[:8]}"
    
    register = client.post(
        "/api/auth/register",
        json={"username": username, "password": "secret123"},
    )
    assert register.status_code == 200

    login = client.post(
        "/api/auth/login",
        json={"username": username, "password": "secret123"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    feed = client.get("/api/feed", headers={"Authorization": f"Bearer {token}"})
    assert feed.status_code == 200
    assert "stories" in feed.json()
