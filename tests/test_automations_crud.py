"""
Tests for automations CRUD endpoints.
Covers the REST layer on top of the automation engine.
"""
import pytest
from fastapi.testclient import TestClient


class TestAutomationsCRUD:

    def _create_automation(self, client, test_account, admin_headers, nombre="Test Auto"):
        return client.post(
            f"/api/v1/admin/accounts/{test_account.id}/automations",
            headers=admin_headers,
            json={
                "nombre": nombre,
                "trigger_tipo": "lead_created",
                "activo": True,
                "conditions": [
                    {"campo": "estado", "operador": "equals", "valor": "nuevo", "orden": 0}
                ],
                "actions": [
                    {"tipo": "update_field", "config": {"campo": "procesado", "valor": "si"}, "orden": 0}
                ],
            },
        )

    def test_create_automation_success(self, client: TestClient, test_account, admin_headers):
        resp = self._create_automation(client, test_account, admin_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["nombre"] == "Test Auto"
        assert data["trigger_tipo"] == "lead_created"
        assert data["activo"] is True
        assert len(data["conditions"]) == 1
        assert len(data["actions"]) == 1

    def test_create_automation_invalid_trigger_returns_400(
        self, client: TestClient, test_account, admin_headers
    ):
        resp = client.post(
            f"/api/v1/admin/accounts/{test_account.id}/automations",
            headers=admin_headers,
            json={
                "nombre": "Bad",
                "trigger_tipo": "trigger_that_does_not_exist",
                "activo": True,
                "conditions": [],
                "actions": [],
            },
        )
        assert resp.status_code == 400

    def test_create_automation_invalid_action_type_returns_400(
        self, client: TestClient, test_account, admin_headers
    ):
        resp = client.post(
            f"/api/v1/admin/accounts/{test_account.id}/automations",
            headers=admin_headers,
            json={
                "nombre": "Bad Action",
                "trigger_tipo": "lead_created",
                "activo": True,
                "conditions": [],
                "actions": [
                    {"tipo": "do_magic", "config": {}, "orden": 0}
                ],
            },
        )
        assert resp.status_code == 400

    def test_list_automations(self, client: TestClient, test_account, admin_headers):
        self._create_automation(client, test_account, admin_headers, "Auto 1")
        self._create_automation(client, test_account, admin_headers, "Auto 2")

        resp = client.get(
            f"/api/v1/admin/accounts/{test_account.id}/automations",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert len(data["items"]) >= 2

    def test_get_automation_detail(self, client: TestClient, test_account, admin_headers):
        create_resp = self._create_automation(client, test_account, admin_headers)
        auto_id = create_resp.json()["id"]

        resp = client.get(
            f"/api/v1/admin/automations/{auto_id}",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == auto_id

    def test_get_nonexistent_automation_returns_404(
        self, client: TestClient, admin_headers
    ):
        import uuid
        resp = client.get(
            f"/api/v1/admin/automations/{uuid.uuid4()}",
            headers=admin_headers,
        )
        assert resp.status_code == 404

    def test_update_automation(self, client: TestClient, test_account, admin_headers):
        auto_id = self._create_automation(client, test_account, admin_headers).json()["id"]

        resp = client.put(
            f"/api/v1/admin/automations/{auto_id}",
            headers=admin_headers,
            json={"nombre": "Updated Name", "activo": False},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["nombre"] == "Updated Name"
        assert data["activo"] is False

    def test_delete_automation(self, client: TestClient, test_account, admin_headers):
        auto_id = self._create_automation(client, test_account, admin_headers).json()["id"]

        del_resp = client.delete(
            f"/api/v1/admin/automations/{auto_id}",
            headers=admin_headers,
        )
        assert del_resp.status_code in (200, 204)

        # Verify it's gone
        get_resp = client.get(
            f"/api/v1/admin/automations/{auto_id}",
            headers=admin_headers,
        )
        assert get_resp.status_code == 404

    def test_automations_isolated_per_account(
        self, client: TestClient, test_account, admin_headers, db_session
    ):
        from app.models.account import Account
        account_b = Account(nombre="Account B Autos", api_key="key-b-autos", activo=True)
        db_session.add(account_b)
        db_session.commit()

        self._create_automation(client, test_account, admin_headers)

        resp = client.get(
            f"/api/v1/admin/accounts/{account_b.id}/automations",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        # Account B should have no automations
        assert resp.json()["items"] == []


class TestAutomationMeta:
    """Test the metadata endpoint that lists valid trigger types and operators."""

    def test_get_automation_meta(self, client: TestClient, admin_headers):
        resp = client.get("/api/v1/admin/automations/meta", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "trigger_types" in data
        assert "action_types" in data
        assert "condition_operators" in data
        assert "lead_created" in data["trigger_types"]


class TestAutomationLogs:
    """Test that execution logs are accessible via the API."""

    def test_list_automation_logs(self, client: TestClient, test_account, admin_headers, db_session):
        from app.models.automation import Automation, AutomationLog

        auto = Automation(
            cuenta_id=test_account.id,
            nombre="Logged Auto",
            trigger_tipo="lead_created",
            activo=True,
        )
        db_session.add(auto)
        db_session.flush()

        log = AutomationLog(
            automation_id=auto.id,
            trigger_evento="lead_created",
            conditions_passed=True,
        )
        db_session.add(log)
        db_session.commit()

        resp = client.get(
            f"/api/v1/admin/automations/{auto.id}/logs",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert len(data["items"]) >= 1
        assert data["items"][0]["conditions_passed"] is True
