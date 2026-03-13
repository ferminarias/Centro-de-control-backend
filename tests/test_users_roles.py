"""
Tests for user and role management endpoints.
"""
import pytest
from fastapi.testclient import TestClient


class TestUserManagement:
    """CRUD operations for users."""

    def test_create_user_success(self, client: TestClient, test_account, admin_headers, test_role):
        response = client.post(
            f"/api/v1/admin/accounts/{test_account.id}/users",
            headers=admin_headers,
            json={
                "nombre": "Maria",
                "apellido": "Garcia",
                "email": "maria.garcia@example.com",
                "username": "mgarcia",
                "password": "SecurePass123!",
                "role_id": str(test_role.id),
                "activo": True,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "maria.garcia@example.com"
        assert data["nombre"] == "Maria"
        assert data["cuenta_id"] == str(test_account.id)
        # Password must NOT appear in response
        assert "password" not in data
        assert "password_hash" not in data

    def test_create_user_duplicate_email_returns_409(
        self, client: TestClient, test_account, admin_headers, test_user
    ):
        response = client.post(
            f"/api/v1/admin/accounts/{test_account.id}/users",
            headers=admin_headers,
            json={
                "nombre": "Otro",
                "email": test_user.email,  # duplicate
                "username": "otro_username",
                "password": "Pass123!",
            },
        )
        assert response.status_code == 409

    def test_create_user_invalid_role_returns_404(
        self, client: TestClient, test_account, admin_headers
    ):
        import uuid
        response = client.post(
            f"/api/v1/admin/accounts/{test_account.id}/users",
            headers=admin_headers,
            json={
                "nombre": "Test",
                "email": "roletest@example.com",
                "username": "roletest",
                "password": "Pass123!",
                "role_id": str(uuid.uuid4()),  # non-existent role
            },
        )
        assert response.status_code == 404

    def test_create_user_account_not_found_returns_404(
        self, client: TestClient, admin_headers
    ):
        import uuid
        response = client.post(
            f"/api/v1/admin/accounts/{uuid.uuid4()}/users",
            headers=admin_headers,
            json={
                "nombre": "Test",
                "email": "test@example.com",
                "username": "testuser",
                "password": "Pass123!",
            },
        )
        assert response.status_code == 404

    def test_list_users(self, client: TestClient, test_account, admin_headers, test_user):
        response = client.get(
            f"/api/v1/admin/accounts/{test_account.id}/users",
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert any(u["email"] == test_user.email for u in data["items"])

    def test_update_user(self, client: TestClient, test_account, admin_headers, test_user):
        response = client.put(
            f"/api/v1/admin/users/{test_user.id}",
            headers=admin_headers,
            json={"nombre": "Nombre Actualizado"},
        )
        assert response.status_code == 200
        assert response.json()["nombre"] == "Nombre Actualizado"

    def test_deactivate_user(self, client: TestClient, test_account, admin_headers, db_session, test_role):
        """Deactivating a user should prevent login."""
        from app.models.user import User
        from app.core.auth import hash_password

        user = User(
            cuenta_id=test_account.id,
            role_id=test_role.id,
            email="to.deactivate@example.com",
            hashed_password=hash_password("pass123"),
            nombre="ToDeactivate",
            activo=True,
        )
        db_session.add(user)
        db_session.commit()

        # Deactivate
        response = client.put(
            f"/api/v1/admin/users/{user.id}",
            headers=admin_headers,
            json={"activo": False},
        )
        assert response.status_code == 200
        assert response.json()["activo"] is False

        # Login should now fail
        login_resp = client.post(
            "/api/v1/auth/login",
            json={"email": "to.deactivate@example.com", "password": "pass123"},
        )
        assert login_resp.status_code == 401

    def test_users_are_isolated_per_account(
        self, client: TestClient, admin_headers, db_session
    ):
        """Users from account A should not appear in account B's user list."""
        from app.models.account import Account

        account_b = Account(nombre="Account B", api_key="key-b-users", activo=True)
        db_session.add(account_b)
        db_session.commit()

        response = client.get(
            f"/api/v1/admin/accounts/{account_b.id}/users",
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.json()
        # Account B should have no users
        assert data["items"] == [] or all(
            str(u["cuenta_id"]) == str(account_b.id) for u in data["items"]
        )


class TestRoleManagement:
    """CRUD operations for roles."""

    def test_create_role(self, client: TestClient, test_account, admin_headers):
        response = client.post(
            f"/api/v1/admin/accounts/{test_account.id}/roles",
            headers=admin_headers,
            json={
                "nombre": "Agente",
                "permisos": ["leads:read", "leads:update"],
                "activo": True,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["nombre"] == "Agente"
        assert "leads:read" in data["permisos"]

    def test_list_roles(self, client: TestClient, test_account, admin_headers, test_role):
        response = client.get(
            f"/api/v1/admin/accounts/{test_account.id}/roles",
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert any(r["id"] == str(test_role.id) for r in data["items"])

    def test_update_role_permissions(
        self, client: TestClient, test_account, admin_headers, db_session
    ):
        from app.models.role import Role

        role = Role(
            cuenta_id=test_account.id,
            nombre="Limited",
            permisos=["leads:read"],
            activo=True,
        )
        db_session.add(role)
        db_session.commit()

        response = client.put(
            f"/api/v1/admin/roles/{role.id}",
            headers=admin_headers,
            json={"permisos": ["leads:read", "leads:update", "leads:create"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert "leads:create" in data["permisos"]

    def test_roles_are_isolated_per_account(
        self, client: TestClient, admin_headers, db_session
    ):
        from app.models.account import Account

        account_b = Account(nombre="Account B Roles", api_key="key-b-roles", activo=True)
        db_session.add(account_b)
        db_session.commit()

        response = client.get(
            f"/api/v1/admin/accounts/{account_b.id}/roles",
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert all(
            str(r["cuenta_id"]) == str(account_b.id) for r in data["items"]
        )


class TestPermissionEnforcement:
    """Verify RBAC prevents unauthorized actions."""

    def test_user_without_permission_gets_403(
        self, client: TestClient, db_session, test_account
    ):
        """A user with only 'leads:read' cannot create leads."""
        from app.models.role import Role
        from app.models.user import User
        from app.core.auth import hash_password, create_access_token

        restricted_role = Role(
            cuenta_id=test_account.id,
            nombre="ReadOnly",
            permisos=["leads:read"],
            activo=True,
        )
        db_session.add(restricted_role)
        db_session.flush()

        user = User(
            cuenta_id=test_account.id,
            role_id=restricted_role.id,
            email="readonly@example.com",
            hashed_password=hash_password("pass"),
            nombre="ReadOnly User",
            activo=True,
        )
        db_session.add(user)
        db_session.commit()

        token = create_access_token(
            user_id=user.id,
            cuenta_id=test_account.id,
            role_id=restricted_role.id,
            permisos=["leads:read"],
        )
        headers = {"Authorization": f"Bearer {token}"}

        # Should be forbidden — creating leads requires leads:create
        response = client.post(
            f"/api/v1/admin/accounts/{test_account.id}/leads",
            headers=headers,
            json={"datos": {"nombre": "Test"}},
        )
        assert response.status_code == 403

    def test_wildcard_permission_grants_full_access(
        self, client: TestClient, test_account, auth_headers
    ):
        """User with ['*'] permission can do anything."""
        response = client.get(
            f"/api/v1/admin/accounts/{test_account.id}/leads",
            headers=auth_headers,
        )
        # Should not be 403
        assert response.status_code != 403

    def test_module_wildcard_grants_module_access(
        self, client: TestClient, db_session, test_account
    ):
        """User with ['leads:*'] can access any leads endpoint."""
        from app.models.role import Role
        from app.models.user import User
        from app.core.auth import hash_password, create_access_token

        role = Role(
            cuenta_id=test_account.id,
            nombre="LeadsAdmin",
            permisos=["leads:*"],
            activo=True,
        )
        db_session.add(role)
        db_session.flush()

        user = User(
            cuenta_id=test_account.id,
            role_id=role.id,
            email="leadsadmin@example.com",
            hashed_password=hash_password("pass"),
            nombre="Leads Admin",
            activo=True,
        )
        db_session.add(user)
        db_session.commit()

        token = create_access_token(
            user_id=user.id,
            cuenta_id=test_account.id,
            role_id=role.id,
            permisos=["leads:*"],
        )
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get(
            f"/api/v1/admin/accounts/{test_account.id}/leads",
            headers=headers,
        )
        assert response.status_code != 403
