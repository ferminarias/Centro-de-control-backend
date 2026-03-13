"""
Tests for CRM extras endpoints: Actividades, Tareas, Notas, Tags, AuditLog.
Covers CRUD operations, permission checks, and business rules.
"""
import uuid
import pytest
from fastapi.testclient import TestClient


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _create_lead(db_session, test_account):
    from app.models.lead import Lead
    lead = Lead(cuenta_id=test_account.id, datos={"nombre": "CRM Lead"})
    db_session.add(lead)
    db_session.commit()
    return lead


# ─────────────────────────────────────────────────────────────────────────────
# Actividades
# ─────────────────────────────────────────────────────────────────────────────

class TestActividades:

    def test_list_actividades_empty(self, client: TestClient, test_account, auth_headers):
        resp = client.get(
            f"/api/v1/admin/accounts/{test_account.id}/actividades",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert isinstance(data["items"], list)

    def test_create_actividad(self, client: TestClient, test_account, auth_headers, db_session):
        lead = _create_lead(db_session, test_account)
        resp = client.post(
            f"/api/v1/admin/accounts/{test_account.id}/actividades",
            headers=auth_headers,
            json={
                "lead_id": str(lead.id),
                "tipo": "llamada",
                "descripcion": "Llamada de seguimiento inicial",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["tipo"] == "llamada"
        assert data["lead_id"] == str(lead.id)
        assert "id" in data

    def test_create_actividad_with_all_fields(
        self, client: TestClient, test_account, auth_headers, db_session
    ):
        lead = _create_lead(db_session, test_account)
        resp = client.post(
            f"/api/v1/admin/accounts/{test_account.id}/actividades",
            headers=auth_headers,
            json={
                "lead_id": str(lead.id),
                "tipo": "email",
                "direccion": "saliente",
                "asunto": "Propuesta comercial",
                "descripcion": "Email con propuesta adjunta",
                "resultado": "enviado",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["asunto"] == "Propuesta comercial"

    def test_list_actividades_filtered_by_lead(
        self, client: TestClient, test_account, auth_headers, db_session
    ):
        lead1 = _create_lead(db_session, test_account)
        lead2 = _create_lead(db_session, test_account)

        client.post(
            f"/api/v1/admin/accounts/{test_account.id}/actividades",
            headers=auth_headers,
            json={"lead_id": str(lead1.id), "tipo": "llamada", "descripcion": "Para lead1"},
        )
        client.post(
            f"/api/v1/admin/accounts/{test_account.id}/actividades",
            headers=auth_headers,
            json={"lead_id": str(lead2.id), "tipo": "email", "descripcion": "Para lead2"},
        )

        resp = client.get(
            f"/api/v1/admin/accounts/{test_account.id}/actividades?lead_id={lead1.id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert all(item["lead_id"] == str(lead1.id) for item in items)

    def test_get_actividad(self, client: TestClient, test_account, auth_headers, db_session):
        lead = _create_lead(db_session, test_account)
        create_resp = client.post(
            f"/api/v1/admin/accounts/{test_account.id}/actividades",
            headers=auth_headers,
            json={"lead_id": str(lead.id), "tipo": "reunión", "descripcion": "Reunión"},
        )
        act_id = create_resp.json()["id"]

        resp = client.get(f"/api/v1/admin/actividades/{act_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == act_id

    def test_get_actividad_not_found(self, client: TestClient, auth_headers):
        resp = client.get(
            f"/api/v1/admin/actividades/{uuid.uuid4()}",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_update_actividad(self, client: TestClient, test_account, auth_headers, db_session):
        lead = _create_lead(db_session, test_account)
        create_resp = client.post(
            f"/api/v1/admin/accounts/{test_account.id}/actividades",
            headers=auth_headers,
            json={"lead_id": str(lead.id), "tipo": "llamada", "descripcion": "Original"},
        )
        act_id = create_resp.json()["id"]

        resp = client.put(
            f"/api/v1/admin/actividades/{act_id}",
            headers=auth_headers,
            json={"descripcion": "Actualizada", "resultado": "exitoso"},
        )
        assert resp.status_code == 200
        assert resp.json()["descripcion"] == "Actualizada"

    def test_delete_actividad(self, client: TestClient, test_account, auth_headers, db_session):
        lead = _create_lead(db_session, test_account)
        create_resp = client.post(
            f"/api/v1/admin/accounts/{test_account.id}/actividades",
            headers=auth_headers,
            json={"lead_id": str(lead.id), "tipo": "llamada", "descripcion": "ToDelete"},
        )
        act_id = create_resp.json()["id"]

        del_resp = client.delete(f"/api/v1/admin/actividades/{act_id}", headers=auth_headers)
        assert del_resp.status_code == 204

        get_resp = client.get(f"/api/v1/admin/actividades/{act_id}", headers=auth_headers)
        assert get_resp.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# Tareas
# ─────────────────────────────────────────────────────────────────────────────

class TestTareas:

    def test_list_tareas_empty(self, client: TestClient, test_account, auth_headers):
        resp = client.get(
            f"/api/v1/admin/accounts/{test_account.id}/tareas",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert "items" in resp.json()

    def test_create_tarea(self, client: TestClient, test_account, auth_headers):
        resp = client.post(
            f"/api/v1/admin/accounts/{test_account.id}/tareas",
            headers=auth_headers,
            json={
                "titulo": "Llamar al cliente",
                "tipo": "llamada",
                "prioridad": "alta",
                "estado": "pendiente",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["titulo"] == "Llamar al cliente"
        assert data["prioridad"] == "alta"

    def test_create_tarea_linked_to_lead(
        self, client: TestClient, test_account, auth_headers, db_session
    ):
        lead = _create_lead(db_session, test_account)
        resp = client.post(
            f"/api/v1/admin/accounts/{test_account.id}/tareas",
            headers=auth_headers,
            json={
                "titulo": "Enviar propuesta",
                "lead_id": str(lead.id),
                "tipo": "email",
                "prioridad": "media",
                "estado": "pendiente",
            },
        )
        assert resp.status_code == 201
        assert resp.json()["lead_id"] == str(lead.id)

    def test_update_tarea(self, client: TestClient, test_account, auth_headers):
        tarea_id = client.post(
            f"/api/v1/admin/accounts/{test_account.id}/tareas",
            headers=auth_headers,
            json={"titulo": "Old Title", "prioridad": "baja", "estado": "pendiente"},
        ).json()["id"]

        resp = client.put(
            f"/api/v1/admin/tareas/{tarea_id}",
            headers=auth_headers,
            json={"titulo": "New Title", "prioridad": "alta"},
        )
        assert resp.status_code == 200
        assert resp.json()["titulo"] == "New Title"

    def test_completar_tarea(self, client: TestClient, test_account, auth_headers):
        tarea_id = client.post(
            f"/api/v1/admin/accounts/{test_account.id}/tareas",
            headers=auth_headers,
            json={"titulo": "Tarea a completar", "prioridad": "media", "estado": "pendiente"},
        ).json()["id"]

        resp = client.post(
            f"/api/v1/admin/tareas/{tarea_id}/completar",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["estado"] == "completada"
        assert resp.json()["fecha_completada"] is not None

    def test_delete_tarea(self, client: TestClient, test_account, auth_headers):
        tarea_id = client.post(
            f"/api/v1/admin/accounts/{test_account.id}/tareas",
            headers=auth_headers,
            json={"titulo": "To Delete Task", "prioridad": "baja", "estado": "pendiente"},
        ).json()["id"]

        del_resp = client.delete(f"/api/v1/admin/tareas/{tarea_id}", headers=auth_headers)
        assert del_resp.status_code == 204

    def test_tareas_stats(self, client: TestClient, test_account, auth_headers):
        # Create a couple tasks
        for i in range(3):
            client.post(
                f"/api/v1/admin/accounts/{test_account.id}/tareas",
                headers=auth_headers,
                json={"titulo": f"Task {i}", "prioridad": "media", "estado": "pendiente"},
            )

        resp = client.get(
            f"/api/v1/admin/accounts/{test_account.id}/tareas/stats",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "pendientes" in data
        assert "vencidas" in data
        assert "completadas_hoy" in data
        assert "completadas_semana" in data
        assert data["pendientes"] >= 3

    def test_list_tareas_filtered_by_estado(self, client: TestClient, test_account, auth_headers):
        client.post(
            f"/api/v1/admin/accounts/{test_account.id}/tareas",
            headers=auth_headers,
            json={"titulo": "Pendiente", "prioridad": "media", "estado": "pendiente"},
        )

        resp = client.get(
            f"/api/v1/admin/accounts/{test_account.id}/tareas?estado=pendiente",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert all(item["estado"] == "pendiente" for item in items)


# ─────────────────────────────────────────────────────────────────────────────
# Notas
# ─────────────────────────────────────────────────────────────────────────────

class TestNotas:

    def test_list_notas_for_lead(self, client: TestClient, auth_headers, db_session, test_account):
        lead = _create_lead(db_session, test_account)
        resp = client.get(f"/api/v1/admin/leads/{lead.id}/notas", headers=auth_headers)
        assert resp.status_code == 200
        assert "items" in resp.json()

    def test_create_nota(self, client: TestClient, auth_headers, db_session, test_account):
        lead = _create_lead(db_session, test_account)
        resp = client.post(
            f"/api/v1/admin/leads/{lead.id}/notas",
            headers=auth_headers,
            json={"contenido": "El cliente prefiere contacto por email.", "tipo": "general"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["contenido"] == "El cliente prefiere contacto por email."
        assert data["lead_id"] == str(lead.id)

    def test_create_nota_privada(self, client: TestClient, auth_headers, db_session, test_account):
        lead = _create_lead(db_session, test_account)
        resp = client.post(
            f"/api/v1/admin/leads/{lead.id}/notas",
            headers=auth_headers,
            json={"contenido": "Nota interna.", "es_privada": True},
        )
        assert resp.status_code == 201
        assert resp.json()["es_privada"] is True

    def test_update_nota(self, client: TestClient, auth_headers, db_session, test_account):
        lead = _create_lead(db_session, test_account)
        nota_id = client.post(
            f"/api/v1/admin/leads/{lead.id}/notas",
            headers=auth_headers,
            json={"contenido": "Original"},
        ).json()["id"]

        resp = client.put(
            f"/api/v1/admin/notas/{nota_id}",
            headers=auth_headers,
            json={"contenido": "Actualizada"},
        )
        assert resp.status_code == 200
        assert resp.json()["contenido"] == "Actualizada"

    def test_delete_nota(self, client: TestClient, auth_headers, db_session, test_account):
        lead = _create_lead(db_session, test_account)
        nota_id = client.post(
            f"/api/v1/admin/leads/{lead.id}/notas",
            headers=auth_headers,
            json={"contenido": "To delete"},
        ).json()["id"]

        del_resp = client.delete(f"/api/v1/admin/notas/{nota_id}", headers=auth_headers)
        assert del_resp.status_code == 204

    def test_nota_lead_not_found(self, client: TestClient, auth_headers):
        resp = client.get(
            f"/api/v1/admin/leads/{uuid.uuid4()}/notas",
            headers=auth_headers,
        )
        assert resp.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# Tags
# ─────────────────────────────────────────────────────────────────────────────

class TestTags:

    def test_list_tags_empty(self, client: TestClient, test_account, auth_headers):
        resp = client.get(
            f"/api/v1/admin/accounts/{test_account.id}/tags",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert "items" in resp.json()

    def test_create_tag(self, client: TestClient, test_account, auth_headers):
        resp = client.post(
            f"/api/v1/admin/accounts/{test_account.id}/tags",
            headers=auth_headers,
            json={"nombre": "VIP", "color": "#FFD700"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["nombre"] == "VIP"
        assert data["color"] == "#FFD700"

    def test_update_tag(self, client: TestClient, test_account, auth_headers):
        tag_id = client.post(
            f"/api/v1/admin/accounts/{test_account.id}/tags",
            headers=auth_headers,
            json={"nombre": "OldTag"},
        ).json()["id"]

        resp = client.put(
            f"/api/v1/admin/tags/{tag_id}",
            headers=auth_headers,
            json={"nombre": "NewTag", "color": "#0000FF"},
        )
        assert resp.status_code == 200
        assert resp.json()["nombre"] == "NewTag"

    def test_delete_tag_no_leads(self, client: TestClient, test_account, auth_headers):
        tag_id = client.post(
            f"/api/v1/admin/accounts/{test_account.id}/tags",
            headers=auth_headers,
            json={"nombre": "DeleteMe"},
        ).json()["id"]

        resp = client.delete(f"/api/v1/admin/tags/{tag_id}", headers=auth_headers)
        assert resp.status_code == 204

    def test_assign_tags_to_lead(self, client: TestClient, test_account, auth_headers, db_session):
        lead = _create_lead(db_session, test_account)
        tag_id = client.post(
            f"/api/v1/admin/accounts/{test_account.id}/tags",
            headers=auth_headers,
            json={"nombre": "Priority"},
        ).json()["id"]

        resp = client.put(
            f"/api/v1/admin/leads/{lead.id}/tags",
            headers=auth_headers,
            json={"tag_ids": [tag_id]},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["tags_count"] == 1

    def test_get_lead_tags(self, client: TestClient, test_account, auth_headers, db_session):
        lead = _create_lead(db_session, test_account)
        tag_id = client.post(
            f"/api/v1/admin/accounts/{test_account.id}/tags",
            headers=auth_headers,
            json={"nombre": "GetTag"},
        ).json()["id"]

        client.put(
            f"/api/v1/admin/leads/{lead.id}/tags",
            headers=auth_headers,
            json={"tag_ids": [tag_id]},
        )

        resp = client.get(f"/api/v1/admin/leads/{lead.id}/tags", headers=auth_headers)
        assert resp.status_code == 200
        tag_ids = [t["id"] for t in resp.json()]
        assert tag_id in tag_ids

    def test_assign_empty_tags_clears_lead_tags(
        self, client: TestClient, test_account, auth_headers, db_session
    ):
        lead = _create_lead(db_session, test_account)
        tag_id = client.post(
            f"/api/v1/admin/accounts/{test_account.id}/tags",
            headers=auth_headers,
            json={"nombre": "ToClear"},
        ).json()["id"]

        client.put(
            f"/api/v1/admin/leads/{lead.id}/tags",
            headers=auth_headers,
            json={"tag_ids": [tag_id]},
        )

        # Clear by passing empty list
        clear_resp = client.put(
            f"/api/v1/admin/leads/{lead.id}/tags",
            headers=auth_headers,
            json={"tag_ids": []},
        )
        assert clear_resp.status_code == 200
        assert clear_resp.json()["tags_count"] == 0

        tags = client.get(f"/api/v1/admin/leads/{lead.id}/tags", headers=auth_headers).json()
        assert tags == []


# ─────────────────────────────────────────────────────────────────────────────
# Audit Log
# ─────────────────────────────────────────────────────────────────────────────

class TestAuditLog:

    def test_list_audit_logs_accessible(self, client: TestClient, test_account, auth_headers):
        resp = client.get(
            f"/api/v1/admin/accounts/{test_account.id}/audit-logs",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data

    def test_audit_log_created_after_actividad(
        self, client: TestClient, test_account, auth_headers, db_session
    ):
        lead = _create_lead(db_session, test_account)
        client.post(
            f"/api/v1/admin/accounts/{test_account.id}/actividades",
            headers=auth_headers,
            json={"lead_id": str(lead.id), "tipo": "llamada", "descripcion": "Auditada"},
        )

        resp = client.get(
            f"/api/v1/admin/accounts/{test_account.id}/audit-logs?entidad_tipo=actividad",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) >= 1
        assert all(item["entidad_tipo"] == "actividad" for item in items)

    def test_audit_log_filter_by_accion(
        self, client: TestClient, test_account, auth_headers, db_session
    ):
        lead = _create_lead(db_session, test_account)
        client.post(
            f"/api/v1/admin/accounts/{test_account.id}/actividades",
            headers=auth_headers,
            json={"lead_id": str(lead.id), "tipo": "email", "descripcion": "Filter test"},
        )

        resp = client.get(
            f"/api/v1/admin/accounts/{test_account.id}/audit-logs?accion=create",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert all(item["accion"] == "create" for item in items)
