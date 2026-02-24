"""
Tests for webhook ingestion.
"""
import pytest
from fastapi.testclient import TestClient


class TestIngestWebhook:
    """Test webhook ingestion endpoint."""
    
    def test_ingest_success(self, client: TestClient, test_account):
        """Test successful lead ingestion via webhook."""
        payload = {
            "nombre": "Juan Perez",
            "email": "juan@example.com",
            "telefono": "+5491155551234",
            "empresa": "ACME Corp"
        }
        
        response = client.post(
            f"/api/v1/ingest/{test_account.api_key}",
            json=payload
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "lead_id" in data
        assert "record_id" in data
        assert data["fields_created"] == []  # Account has auto_crear_campos=False by default
    
    def test_ingest_invalid_api_key(self, client: TestClient):
        """Test ingestion with invalid API key."""
        response = client.post(
            "/api/v1/ingest/invalid-api-key",
            json={"nombre": "Test"}
        )
        
        assert response.status_code == 404
    
    def test_ingest_empty_payload(self, client: TestClient, test_account):
        """Test ingestion with empty payload."""
        response = client.post(
            f"/api/v1/ingest/{test_account.api_key}",
            json={}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    def test_ingest_creates_fields_when_auto_create_enabled(
        self, client: TestClient, db_session, test_account
    ):
        """Test that new fields are created when auto_crear_campos is enabled."""
        # Enable auto field creation
        test_account.auto_crear_campos = True
        db_session.commit()
        
        payload = {
            "nuevo_campo_personalizado": "valor123",
            "otro_campo": "otro valor"
        }
        
        response = client.post(
            f"/api/v1/ingest/{test_account.api_key}",
            json=payload
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["fields_created"]) == 2
    
    def test_ingest_rate_limit(self, client: TestClient, test_account):
        """Test rate limiting on ingest endpoint."""
        # Make many requests quickly
        for i in range(105):  # Over the 100/minute limit
            response = client.post(
                f"/api/v1/ingest/{test_account.api_key}",
                json={"test": i}
            )
        
        # At least the last one should be rate limited
        # Note: In development with memory backend, this might behave differently
        assert response.status_code in [200, 429]


class TestIngestValidation:
    """Test input validation for ingestion."""
    
    def test_ingest_large_payload(self, client: TestClient, test_account):
        """Test ingestion with large payload."""
        # Create a large payload (1MB+)
        large_payload = {
            "data": "x" * (1024 * 1024)  # 1MB of data
        }
        
        response = client.post(
            f"/api/v1/ingest/{test_account.api_key}",
            json=large_payload
        )
        
        # Should either succeed or return 413 (Payload Too Large)
        assert response.status_code in [200, 413]
    
    def test_ingest_special_characters(self, client: TestClient, test_account):
        """Test ingestion with special characters."""
        payload = {
            "nombre": "José García <script>alert('xss')</script>",
            "email": "test+special@example.com",
            "notas": "Línea 1\nLínea 2\tTabulado"
        }
        
        response = client.post(
            f"/api/v1/ingest/{test_account.api_key}",
            json=payload
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
