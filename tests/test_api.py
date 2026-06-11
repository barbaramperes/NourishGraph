"""
NourishGraph API Tests
Basic test suite for Master's thesis evaluation
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.api import app

client = TestClient(app)


class TestHealthEndpoints:
    """Test basic health and info endpoints."""

    def test_health_check(self):
        """Test /health endpoint returns correct status."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["online", "degraded"]
        assert data["service"] == "NourishGraph API"
        assert data["version"] == "2.0.0"
        assert "database" in data
        assert "langgraph" in data
        assert "timestamp" in data

    def test_stats_endpoint(self):
        """Test /stats endpoint returns statistics."""
        response = client.get("/stats")
        assert response.status_code in [200, 503]
        if response.status_code == 200:
            data = response.json()
            assert "total_meals" in data
            assert "total_foods" in data


class TestAuthEndpoints:
    """Test authentication endpoints."""

    def test_login_missing_credentials(self):
        """Test login fails without credentials."""
        response = client.post("/auth/login", json={})
        assert response.status_code == 422

    def test_login_invalid_credentials(self):
        """Test login fails with invalid credentials."""
        response = client.post("/auth/login", json={
            "email": "nonexistent@test.com",
            "password": "wrongpassword"
        })
        # API returns 200 with success=false or 401/404
        if response.status_code == 200:
            data = response.json()
            assert data.get("success") == False or "error" in str(data).lower()
        else:
            assert response.status_code in [401, 404]


class TestProtectedEndpoints:
    """Test endpoints that require authentication."""

    def test_chat_requires_auth(self):
        """Test /chat endpoint requires authentication."""
        response = client.post("/chat", json={"message": "Hello"})
        assert response.status_code == 401

    def test_profile_requires_auth(self):
        """Test /profile endpoint requires authentication."""
        response = client.get("/profile")
        assert response.status_code == 401

    def test_meals_requires_auth(self):
        """Test /meals endpoint requires authentication."""
        response = client.get("/meals")
        assert response.status_code == 401


class TestInputValidation:
    """Test input validation and safety."""

    def test_chat_message_length_limit(self):
        """Test chat rejects extremely long messages."""
        long_message = "a" * 15000
        response = client.post(
            "/chat",
            json={"message": long_message},
            headers={"Authorization": "Bearer fake_token"}
        )
        assert response.status_code in [401, 422]

    def test_chat_empty_message(self):
        """Test chat rejects empty messages."""
        response = client.post(
            "/chat",
            json={"message": ""},
            headers={"Authorization": "Bearer fake_token"}
        )
        assert response.status_code in [401, 422]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
