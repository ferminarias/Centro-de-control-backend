"""
Tests for authentication and authorization.
"""
import pytest
from fastapi.testclient import TestClient


class TestAuthentication:
    """Test user authentication (JWT)."""
    
    def test_login_success(self, client: TestClient, test_user):
        """Test successful login returns valid token."""
        response = client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "testpassword123"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"
        assert "user" in data
        assert data["user"]["email"] == "test@example.com"
    
    def test_login_wrong_password(self, client: TestClient):
        """Test login with wrong password returns 401."""
        response = client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "wrongpassword"
        })
        
        assert response.status_code == 401
        assert "detail" in response.json()
    
    def test_login_nonexistent_user(self, client: TestClient):
        """Test login with non-existent user returns 401."""
        response = client.post("/api/v1/auth/login", json={
            "email": "nonexistent@example.com",
            "password": "somepassword"
        })
        
        assert response.status_code == 401
    
    def test_login_invalid_email_format(self, client: TestClient):
        """Test login with invalid email format returns 422."""
        response = client.post("/api/v1/auth/login", json={
            "email": "not-an-email",
            "password": "password123"
        })
        
        assert response.status_code == 422
    
    def test_me_endpoint_success(self, client: TestClient, auth_headers):
        """Test /me endpoint with valid token."""
        response = client.get("/api/v1/auth/me", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"
        assert "id" in data
        assert "permisos" in data
    
    def test_me_endpoint_no_token(self, client: TestClient):
        """Test /me endpoint without token returns 401."""
        response = client.get("/api/v1/auth/me")
        
        assert response.status_code == 401
    
    def test_me_endpoint_invalid_token(self, client: TestClient):
        """Test /me endpoint with invalid token returns 401."""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid-token"}
        )
        
        assert response.status_code == 401


class TestAdminAuthentication:
    """Test admin API key authentication."""
    
    def test_admin_endpoint_with_valid_key(self, client: TestClient, test_account, admin_headers):
        """Test admin endpoint with valid API key."""
        # This test requires ADMIN_API_KEY to be set
        response = client.get(
            f"/api/v1/admin/accounts/{test_account.id}/leads",
            headers=admin_headers
        )
        # Should not be 403 (could be 200 if empty or other valid response)
        assert response.status_code != 403
    
    def test_admin_endpoint_without_key(self, client: TestClient, test_account):
        """Test admin endpoint without API key returns 403."""
        # Skip in development mode where auth is bypassed
        import os
        if os.getenv("ENVIRONMENT") == "development" and not os.getenv("ADMIN_API_KEY"):
            pytest.skip("Auth bypassed in development mode")
        
        response = client.get(f"/api/v1/admin/accounts/{test_account.id}/leads")
        
        assert response.status_code == 403


class TestAuthorization:
    """Test RBAC and permissions."""
    
    def test_access_with_permission(self, client: TestClient, auth_headers):
        """Test accessing resource with required permission."""
        # User has "*" permission (super admin)
        response = client.get("/api/v1/admin/accounts", headers=auth_headers)
        
        # Should have access (not 403)
        assert response.status_code != 403
    
    def test_permission_wildcard(self, client: TestClient, test_user, test_account):
        """Test wildcard permission grants access to all resources."""
        from app.core.auth import create_access_token
        
        # Create token with wildcard permission
        token = create_access_token(
            user_id=test_user.id,
            cuenta_id=test_account.id,
            role_id=test_user.role_id,
            permisos=["*"]
        )
        headers = {"Authorization": f"Bearer {token}"}
        
        response = client.get("/api/v1/leads", headers=headers)
        
        # Should have access with wildcard
        assert response.status_code != 403
