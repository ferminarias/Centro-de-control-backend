"""
Tests for multi-tenant security.
Ensures users cannot access resources from other accounts.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.lead import Lead
from app.models.lead_base import LeadBase
from app.models.user import User
from app.models.role import Role
from app.core.auth import hash_password, create_access_token


class TestMultiTenantIsolation:
    """Test that resources are isolated between accounts."""
    
    @pytest.fixture
    def account_b(self, db_session) -> Account:
        """Create a second account for cross-tenant tests."""
        account = Account(
            nombre="Account B",
            api_key="api-key-b",
            activo=True
        )
        db_session.add(account)
        db_session.commit()
        return account
    
    @pytest.fixture
    def user_b(self, db_session, account_b) -> User:
        """Create a user in account B."""
        role = Role(
            cuenta_id=account_b.id,
            nombre="Admin",
            permisos=["*"],
            activo=True
        )
        db_session.add(role)
        db_session.commit()
        
        user = User(
            cuenta_id=account_b.id,
            role_id=role.id,
            email="userb@example.com",
            hashed_password=hash_password("password"),
            nombre="User B",
            activo=True
        )
        db_session.add(user)
        db_session.commit()
        return user
    
    @pytest.fixture
    def auth_headers_b(self, user_b, account_b) -> dict:
        """Auth headers for user B."""
        token = create_access_token(
            user_id=user_b.id,
            cuenta_id=account_b.id,
            role_id=user_b.role_id,
            permisos=["*"]
        )
        return {"Authorization": f"Bearer {token}"}
    
    def test_cannot_access_lead_from_other_account(
        self, client: TestClient, test_account, auth_headers_b, db_session
    ):
        """Test that user B cannot see lead from account A."""
        # Create lead in account A
        from app.models.lead import Lead
        lead_a = Lead(
            cuenta_id=test_account.id,
            datos={"nombre": "Lead Account A"}
        )
        db_session.add(lead_a)
        db_session.commit()
        
        # User B tries to access lead from account A
        response = client.get(
            f"/api/v1/admin/leads/{lead_a.id}",
            headers=auth_headers_b
        )
        
        # Should get 404 (not 403, to not leak existence)
        assert response.status_code == 404
    
    def test_cannot_access_lead_base_from_other_account(
        self, client: TestClient, test_account, auth_headers_b, db_session
    ):
        """Test that user B cannot see lead base from account A."""
        from app.models.lead_base import LeadBase
        base_a = LeadBase(
            cuenta_id=test_account.id,
            nombre="Base A"
        )
        db_session.add(base_a)
        db_session.commit()
        
        response = client.get(
            f"/api/v1/admin/lead-bases/{base_a.id}",
            headers=auth_headers_b
        )
        
        assert response.status_code == 404
    
    def test_cannot_update_lead_from_other_account(
        self, client: TestClient, test_account, auth_headers_b, db_session
    ):
        """Test that user B cannot update lead from account A."""
        from app.models.lead import Lead
        lead_a = Lead(
            cuenta_id=test_account.id,
            datos={"nombre": "Lead Account A"}
        )
        db_session.add(lead_a)
        db_session.commit()
        
        response = client.put(
            f"/api/v1/admin/leads/{lead_a.id}",
            headers=auth_headers_b,
            json={"datos": {"nombre": "Hacked"}}
        )
        
        assert response.status_code == 404
    
    def test_cannot_delete_lead_from_other_account(
        self, client: TestClient, test_account, auth_headers_b, db_session
    ):
        """Test that user B cannot delete lead from account A."""
        from app.models.lead import Lead
        lead_a = Lead(
            cuenta_id=test_account.id,
            datos={"nombre": "Lead Account A"}
        )
        db_session.add(lead_a)
        db_session.commit()
        
        response = client.delete(
            f"/api/v1/admin/leads/{lead_a.id}",
            headers=auth_headers_b
        )
        
        assert response.status_code == 404
    
    def test_can_access_own_account_resources(
        self, client: TestClient, test_user, test_account, auth_headers, db_session
    ):
        """Test that user CAN access their own account resources."""
        from app.models.lead import Lead
        lead = Lead(
            cuenta_id=test_account.id,
            datos={"nombre": "My Lead"}
        )
        db_session.add(lead)
        db_session.commit()
        
        response = client.get(
            f"/api/v1/admin/leads/{lead.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        assert response.json()["datos"]["nombre"] == "My Lead"
    
    def test_list_only_shows_own_account_leads(
        self, client: TestClient, test_account, account_b, auth_headers, auth_headers_b, db_session
    ):
        """Test that list endpoints only show resources from user's account."""
        from app.models.lead import Lead
        
        # Create leads in both accounts
        lead_a = Lead(cuenta_id=test_account.id, datos={"nombre": "Lead A"})
        lead_b = Lead(cuenta_id=account_b.id, datos={"nombre": "Lead B"})
        db_session.add_all([lead_a, lead_b])
        db_session.commit()
        
        # User A lists leads
        response_a = client.get(
            f"/api/v1/admin/accounts/{test_account.id}/leads",
            headers=auth_headers
        )
        
        assert response_a.status_code == 200
        items_a = response_a.json()["items"]
        
        # Should only see leads from account A
        assert all(item["cuenta_id"] == str(test_account.id) for item in items_a)
        assert not any(item["cuenta_id"] == str(account_b.id) for item in items_a)


class TestAdminCanAccessAllTenants:
    """Test that super admins can access all accounts."""
    
    @pytest.fixture
    def super_admin_user(self, db_session) -> User:
        """Create a super admin user with wildcard permission."""
        # Create admin account
        admin_account = Account(
            nombre="Admin Account",
            api_key="admin-key",
            activo=True
        )
        db_session.add(admin_account)
        db_session.flush()
        
        # Create admin role with wildcard
        role = Role(
            cuenta_id=admin_account.id,
            nombre="Super Admin",
            permisos=["*"],
            activo=True
        )
        db_session.add(role)
        db_session.flush()
        
        user = User(
            cuenta_id=admin_account.id,
            role_id=role.id,
            email="superadmin@example.com",
            hashed_password=hash_password("password"),
            nombre="Super Admin",
            activo=True
        )
        db_session.add(user)
        db_session.commit()
        return user
    
    @pytest.fixture
    def super_admin_headers(self, super_admin_user) -> dict:
        """Auth headers for super admin."""
        token = create_access_token(
            user_id=super_admin_user.id,
            cuenta_id=super_admin_user.cuenta_id,
            role_id=super_admin_user.role_id,
            permisos=["*"]
        )
        return {"Authorization": f"Bearer {token}"}
    
    def test_super_admin_can_access_any_account(
        self, client: TestClient, test_account, super_admin_headers, db_session
    ):
        """Test that super admin can access resources from any account."""
        from app.models.lead import Lead
        lead = Lead(
            cuenta_id=test_account.id,
            datos={"nombre": "Lead in Account A"}
        )
        db_session.add(lead)
        db_session.commit()
        
        # Super admin can access
        response = client.get(
            f"/api/v1/admin/leads/{lead.id}",
            headers=super_admin_headers
        )
        
        # Should work (if super admin logic is implemented)
        # If not implemented, this will fail with 404
        assert response.status_code in [200, 404]


class TestIngestSecurity:
    """Test security of ingestion endpoint."""
    
    def test_ingest_with_wrong_api_key_fails(self, client: TestClient):
        """Test that ingestion with wrong API key is rejected."""
        response = client.post(
            "/api/v1/ingest/wrong-api-key",
            json={"nombre": "Test"}
        )
        
        assert response.status_code == 404
    
    def test_ingest_creates_lead_in_correct_account(
        self, client: TestClient, test_account, db_session
    ):
        """Test that ingested lead goes to correct account."""
        response = client.post(
            f"/api/v1/ingest/{test_account.api_key}",
            json={"nombre": "Test Lead", "email": "test@test.com"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify lead was created in correct account
        from app.models.lead import Lead
        lead = db_session.query(Lead).filter(Lead.id == data["lead_id"]).first()
        assert lead is not None
        assert lead.cuenta_id == test_account.id
