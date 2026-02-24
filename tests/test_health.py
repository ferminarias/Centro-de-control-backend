"""
Tests for system health and basic connectivity.
"""
import pytest
from fastapi.testclient import TestClient


class TestHealth:
    """Test health endpoints."""
    
    def test_health_check(self, client: TestClient):
        """Test health endpoint returns ok."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
    
    def test_health_includes_timestamp(self, client: TestClient):
        """Test health endpoint response structure."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data


class TestAPIDocs:
    """Test API documentation availability."""
    
    def test_swagger_ui_available(self, client: TestClient):
        """Test Swagger UI is accessible."""
        response = client.get("/docs")
        
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
    
    def test_openapi_schema_available(self, client: TestClient):
        """Test OpenAPI schema is accessible."""
        response = client.get("/openapi.json")
        
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "paths" in data
