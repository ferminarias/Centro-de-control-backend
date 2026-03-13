"""
Tests for tipificaciones endpoints.
Covers Tipificacion and Subtipificacion CRUD, lead assignment, and boundary conditions.
"""
import uuid
import pytest
from fastapi.testclient import TestClient


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _create_tip(client, test_account, auth_headers, nombre="Interesado", **kwargs):
    payload = {"nombre": nombre, "activo": True, **kwargs}
    return client.post(
        f"/api/v1/admin/accounts/{test_account.id}/tipificaciones",
        headers=auth_headers,
        json=payload,
    )


def _create_lead(db_session, test_account):
    from app.models.lead import Lead
    lead = Lead(cuenta_id=test_account.id, datos={"nombre": "Lead Tip Test"})
    db_session.add(lead)
    db_session.commit()
    return lead


# ─────────────────────────────────────────────────────────────────────────────
# Tipificacion CRUD
# ─────────────────────────────────────────────────────────────────────────────

class TestTipificacionCRUD:

    def test_list_tipificaciones_empty(self, client: TestClient, test_account, auth_headers):
        resp = client.get(
            f"/api/v1/admin/accounts/{test_account.id}/tipificaciones",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert isinstance(data["items"], list)

    def test_create_tipificacion_basic(self, client: TestClient, test_account, auth_headers):
        resp = _create_tip(client, test_account, auth_headers, nombre="Interesado")
        assert resp.status_code == 201
        data = resp.json()
        assert data["nombre"] == "Interesado"
        assert data["activo"] is True
        assert "id" in data

    def test_create_tipificacion_with_color(self, client: TestClient, test_account, auth_headers):
        resp = _create_tip(client, test_account, auth_headers, nombre="Rechazado", color="#FF0000")
        assert resp.status_code == 201
        assert resp.json()["color"] == "#FF0000"

    def test_create_tipificacion_es_final(self, client: TestClient, test_account, auth_headers):
        resp = _create_tip(client, test_account, auth_headers, nombre="Final", es_final=True)
        assert resp.status_code == 201
        assert resp.json()["es_final"] is True

    def test_list_tipificaciones_shows_created(self, client: TestClient, test_account, auth_headers):
        _create_tip(client, test_account, auth_headers, nombre="Pending")
        _create_tip(client, test_account, auth_headers, nombre="Closed")

        resp = client.get(
            f"/api/v1/admin/accounts/{test_account.id}/tipificaciones",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        names = [item["nombre"] for item in resp.json()["items"]]
        assert "Pending" in names
        assert "Closed" in names

    def test_get_tipificacion_by_id(self, client: TestClient, test_account, auth_headers):
        tip_id = _create_tip(client, test_account, auth_headers, nombre="GetMe").json()["id"]
        resp = client.get(f"/api/v1/admin/tipificaciones/{tip_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == tip_id

    def test_get_tipificacion_not_found(self, client: TestClient, auth_headers):
        resp = client.get(
            f"/api/v1/admin/tipificaciones/{uuid.uuid4()}",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_update_tipificacion(self, client: TestClient, test_account, auth_headers):
        tip_id = _create_tip(client, test_account, auth_headers, nombre="Old Name").json()["id"]

        resp = client.put(
            f"/api/v1/admin/tipificaciones/{tip_id}",
            headers=auth_headers,
            json={"nombre": "New Name", "activo": False},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["nombre"] == "New Name"
        assert data["activo"] is False

    def test_delete_tipificacion_no_leads(self, client: TestClient, test_account, auth_headers):
        tip_id = _create_tip(client, test_account, auth_headers, nombre="ToDelete").json()["id"]

        del_resp = client.delete(
            f"/api/v1/admin/tipificaciones/{tip_id}",
            headers=auth_headers,
        )
        assert del_resp.status_code == 204

        # Verify it's gone
        get_resp = client.get(f"/api/v1/admin/tipificaciones/{tip_id}", headers=auth_headers)
        assert get_resp.status_code == 404

    def test_delete_tipificacion_with_leads_blocked(
        self, client: TestClient, test_account, auth_headers, db_session
    ):
        tip_id = _create_tip(client, test_account, auth_headers, nombre="InUse").json()["id"]

        # Assign lead to this tipificacion
        lead = _create_lead(db_session, test_account)
        from app.models.lead import Lead
        db_session.query(Lead).filter(Lead.id == lead.id).update(
            {"tipificacion_id": uuid.UUID(tip_id)}
        )
        db_session.commit()

        del_resp = client.delete(
            f"/api/v1/admin/tipificaciones/{tip_id}",
            headers=auth_headers,
        )
        assert del_resp.status_code == 400
        assert "lead" in del_resp.json()["detail"].lower()


# ─────────────────────────────────────────────────────────────────────────────
# Subtipificacion CRUD
# ─────────────────────────────────────────────────────────────────────────────

class TestSubtipificacionCRUD:

    def _create_parent(self, client, test_account, auth_headers, nombre="Parent", es_final=False):
        return _create_tip(client, test_account, auth_headers, nombre=nombre, es_final=es_final)

    def test_create_subtipificacion(self, client: TestClient, test_account, auth_headers):
        parent_id = self._create_parent(client, test_account, auth_headers).json()["id"]

        resp = client.post(
            f"/api/v1/admin/tipificaciones/{parent_id}/subtipificaciones",
            headers=auth_headers,
            json={"nombre": "Sub A", "activo": True},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["nombre"] == "Sub A"
        assert data["tipificacion_id"] == parent_id

    def test_create_subtipificacion_under_final_returns_400(
        self, client: TestClient, test_account, auth_headers
    ):
        parent_id = self._create_parent(
            client, test_account, auth_headers, nombre="FinalParent", es_final=True
        ).json()["id"]

        resp = client.post(
            f"/api/v1/admin/tipificaciones/{parent_id}/subtipificaciones",
            headers=auth_headers,
            json={"nombre": "Sub B", "activo": True},
        )
        assert resp.status_code == 400

    def test_list_subtipificaciones(self, client: TestClient, test_account, auth_headers):
        parent_id = self._create_parent(client, test_account, auth_headers, nombre="Parent2").json()["id"]
        client.post(
            f"/api/v1/admin/tipificaciones/{parent_id}/subtipificaciones",
            headers=auth_headers,
            json={"nombre": "Sub X", "activo": True},
        )
        client.post(
            f"/api/v1/admin/tipificaciones/{parent_id}/subtipificaciones",
            headers=auth_headers,
            json={"nombre": "Sub Y", "activo": True},
        )

        resp = client.get(
            f"/api/v1/admin/tipificaciones/{parent_id}/subtipificaciones",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert len(data["items"]) == 2

    def test_update_subtipificacion(self, client: TestClient, test_account, auth_headers):
        parent_id = self._create_parent(client, test_account, auth_headers, nombre="Parent3").json()["id"]
        sub_id = client.post(
            f"/api/v1/admin/tipificaciones/{parent_id}/subtipificaciones",
            headers=auth_headers,
            json={"nombre": "Sub Old", "activo": True},
        ).json()["id"]

        resp = client.put(
            f"/api/v1/admin/subtipificaciones/{sub_id}",
            headers=auth_headers,
            json={"nombre": "Sub New", "activo": False},
        )
        assert resp.status_code == 200
        assert resp.json()["nombre"] == "Sub New"
        assert resp.json()["activo"] is False

    def test_delete_subtipificacion_no_leads(self, client: TestClient, test_account, auth_headers):
        parent_id = self._create_parent(client, test_account, auth_headers, nombre="Parent4").json()["id"]
        sub_id = client.post(
            f"/api/v1/admin/tipificaciones/{parent_id}/subtipificaciones",
            headers=auth_headers,
            json={"nombre": "ToDeleteSub", "activo": True},
        ).json()["id"]

        resp = client.delete(f"/api/v1/admin/subtipificaciones/{sub_id}", headers=auth_headers)
        assert resp.status_code == 204

    def test_delete_subtipificacion_with_leads_blocked(
        self, client: TestClient, test_account, auth_headers, db_session
    ):
        parent_id = self._create_parent(client, test_account, auth_headers, nombre="Parent5").json()["id"]
        sub_id = client.post(
            f"/api/v1/admin/tipificaciones/{parent_id}/subtipificaciones",
            headers=auth_headers,
            json={"nombre": "SubInUse", "activo": True},
        ).json()["id"]

        lead = _create_lead(db_session, test_account)
        from app.models.lead import Lead
        db_session.query(Lead).filter(Lead.id == lead.id).update(
            {"subtipificacion_id": uuid.UUID(sub_id)}
        )
        db_session.commit()

        resp = client.delete(f"/api/v1/admin/subtipificaciones/{sub_id}", headers=auth_headers)
        assert resp.status_code == 400


# ─────────────────────────────────────────────────────────────────────────────
# Lead Tipificacion Assignment
# ─────────────────────────────────────────────────────────────────────────────

class TestLeadTipificacionAssignment:

    def test_assign_tipificacion_to_lead(
        self, client: TestClient, test_account, auth_headers, db_session
    ):
        lead = _create_lead(db_session, test_account)
        tip_id = _create_tip(client, test_account, auth_headers, nombre="TipAssign").json()["id"]

        resp = client.put(
            f"/api/v1/admin/leads/{lead.id}/tipificacion",
            headers=auth_headers,
            json={"tipificacion_id": tip_id},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["tipificacion_id"] == tip_id

    def test_assign_subtipificacion_auto_sets_tipificacion(
        self, client: TestClient, test_account, auth_headers, db_session
    ):
        lead = _create_lead(db_session, test_account)
        parent_id = _create_tip(client, test_account, auth_headers, nombre="ParentAuto").json()["id"]
        sub_id = client.post(
            f"/api/v1/admin/tipificaciones/{parent_id}/subtipificaciones",
            headers=auth_headers,
            json={"nombre": "SubAuto", "activo": True},
        ).json()["id"]

        resp = client.put(
            f"/api/v1/admin/leads/{lead.id}/tipificacion",
            headers=auth_headers,
            json={"subtipificacion_id": sub_id},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        # tipificacion_id should be auto-filled from sub
        assert data["tipificacion_id"] == parent_id

    def test_assign_mismatched_sub_returns_400(
        self, client: TestClient, test_account, auth_headers, db_session
    ):
        lead = _create_lead(db_session, test_account)
        tip1_id = _create_tip(client, test_account, auth_headers, nombre="Tip1").json()["id"]
        tip2_id = _create_tip(client, test_account, auth_headers, nombre="Tip2").json()["id"]
        sub_of_tip2 = client.post(
            f"/api/v1/admin/tipificaciones/{tip2_id}/subtipificaciones",
            headers=auth_headers,
            json={"nombre": "SubOf2", "activo": True},
        ).json()["id"]

        resp = client.put(
            f"/api/v1/admin/leads/{lead.id}/tipificacion",
            headers=auth_headers,
            json={"tipificacion_id": tip1_id, "subtipificacion_id": sub_of_tip2},
        )
        assert resp.status_code == 400

    def test_assign_lead_not_found_returns_404(self, client: TestClient, auth_headers, test_account):
        tip_id = _create_tip(client, test_account, auth_headers, nombre="TipNF").json()["id"]
        resp = client.put(
            f"/api/v1/admin/leads/{uuid.uuid4()}/tipificacion",
            headers=auth_headers,
            json={"tipificacion_id": tip_id},
        )
        assert resp.status_code == 404

    def test_bulk_tipificacion(
        self, client: TestClient, test_account, auth_headers, db_session
    ):
        lead1 = _create_lead(db_session, test_account)
        lead2 = _create_lead(db_session, test_account)
        tip_id = _create_tip(client, test_account, auth_headers, nombre="BulkTip").json()["id"]

        resp = client.post(
            "/api/v1/admin/leads/bulk-tipificacion",
            headers=auth_headers,
            json={
                "lead_ids": [str(lead1.id), str(lead2.id)],
                "tipificacion_id": tip_id,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["updated"] == 2


# ─────────────────────────────────────────────────────────────────────────────
# Stats
# ─────────────────────────────────────────────────────────────────────────────

class TestTipificacionStats:

    def test_get_stats(self, client: TestClient, test_account, auth_headers):
        _create_tip(client, test_account, auth_headers, nombre="StatTip")

        resp = client.get(
            f"/api/v1/admin/accounts/{test_account.id}/tipificaciones/stats",
            headers=auth_headers,
        )
        assert resp.status_code == 200
