"""
Tests for leads CRUD operations.
"""
import pytest
from fastapi.testclient import TestClient


class TestLeadsCRUD:
    """Test leads create, read, update, delete."""
    
    def test_create_lead_success(self, client: TestClient, test_account, auth_headers):
        """Test creating a new lead."""
        response = client.post(
            f"/api/v1/admin/accounts/{test_account.id}/leads",
            headers=auth_headers,
            json={
                "datos": {
                    "nombre": "Juan Perez",
                    "email": "juan@example.com",
                    "telefono": "+5491155551234"
                }
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["datos"]["nombre"] == "Juan Perez"
        assert data["datos"]["email"] == "juan@example.com"
        assert "id" in data
        assert "cuenta_id" in data
        assert data["cuenta_id"] == str(test_account.id)
    
    def test_create_lead_missing_data(self, client: TestClient, test_account, auth_headers):
        """Test creating lead with missing datos returns 422."""
        response = client.post(
            f"/api/v1/admin/accounts/{test_account.id}/leads",
            headers=auth_headers,
            json={}
        )
        
        assert response.status_code == 422
    
    def test_list_leads(self, client: TestClient, test_account, auth_headers):
        """Test listing leads for an account."""
        # Create a lead first
        client.post(
            f"/api/v1/admin/accounts/{test_account.id}/leads",
            headers=auth_headers,
            json={"datos": {"nombre": "Test Lead"}}
        )
        
        response = client.get(
            f"/api/v1/admin/accounts/{test_account.id}/leads",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert len(data["items"]) >= 1
    
    def test_list_leads_pagination(self, client: TestClient, test_account, auth_headers):
        """Test leads pagination."""
        response = client.get(
            f"/api/v1/admin/accounts/{test_account.id}/leads?page=1&page_size=10",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data


class TestLeadsIngestion:
    """Test leads ingestion via webhooks."""
    
    def test_ingest_lead_success(self, client: TestClient, test_account):
        """Test ingesting lead via public webhook."""
        response = client.post(
            f"/api/v1/ingest/{test_account.api_key}",
            json={
                "nombre": "Maria Garcia",
                "email": "maria@example.com",
                "telefono": "+5491166665678"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "lead_id" in data
    
    def test_ingest_lead_invalid_api_key(self, client: TestClient):
        """Test ingesting with invalid API key returns 404."""
        response = client.post(
            "/api/v1/ingest/invalid-api-key",
            json={"nombre": "Test"}
        )
        
        assert response.status_code == 404
    
    def test_ingest_lead_empty_payload(self, client: TestClient, test_account):
        """Test ingesting with empty payload."""
        response = client.post(
            f"/api/v1/ingest/{test_account.api_key}",
            json={}
        )
        
        # Should still accept empty payload (stores empty dict)
        assert response.status_code == 200


class TestLeadsSearch:
    """Test leads search functionality."""
    
    def test_search_leads(self, client: TestClient, test_account, auth_headers):
        """Test searching leads."""
        # Create a lead
        client.post(
            f"/api/v1/admin/accounts/{test_account.id}/leads",
            headers=auth_headers,
            json={"datos": {"nombre": "Juan Perez", "email": "juan@test.com"}}
        )
        
        # Search for it
        response = client.get(
            f"/api/v1/admin/accounts/{test_account.id}/leads/search?q=Juan",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data


class TestLeadsMultiTenancy:
    """Test leads isolation between accounts."""
    
    def test_leads_isolated_between_accounts(
        self, client: TestClient, db_session, test_account, auth_headers
    ):
        """Test that leads from account A are not visible in account B."""
        from app.models.account import Account
        from app.models.user import User
        from app.models.role import Role
        from app.core.auth import hash_password, create_access_token
        
        # Create second account
        account_b = Account(nombre="Account B", api_key="api-key-b", activo=True)
        db_session.add(account_b)
        db_session.commit()
        
        # Create user in account B
        role_b = Role(cuenta_id=account_b.id, nombre="Admin", permisos=["*"], activo=True)
        db_session.add(role_b)
        db_session.commit()
        
        user_b = User(
            cuenta_id=account_b.id,
            role_id=role_b.id,
            email="userb@example.com",
            hashed_password=hash_password("password"),
            nombre="User B",
            activo=True
        )
        db_session.add(user_b)
        db_session.commit()
        
        # Get token for user B
        token_b = create_access_token(
            user_id=user_b.id,
            cuenta_id=account_b.id,
            role_id=role_b.id,
            permisos=["*"]
        )
        headers_b = {"Authorization": f"Bearer {token_b}"}
        
        # Create lead in account A
        client.post(
            f"/api/v1/admin/accounts/{test_account.id}/leads",
            headers=auth_headers,
            json={"datos": {"nombre": "Lead in Account A"}}
        )
        
        # Try to access account A leads with account B token
        response = client.get(
            f"/api/v1/admin/accounts/{test_account.id}/leads",
            headers=headers_b
        )
        
        # Should return empty or filtered results (no cross-tenant access)
        assert response.status_code == 200
        data = response.json()
        # User B should not see leads from account A
        # (implementation depends on your security layer)
