"""
Tests for the automation engine.

Splits into:
  - Unit tests for _evaluate_conditions (pure logic, no DB)
  - Integration tests for run_automations (needs DB fixtures)
"""
import uuid
import pytest
from unittest.mock import MagicMock, patch

from app.services.automation_engine import (
    _evaluate_conditions,
    _action_update_field,
    _action_move_to_base,
    _action_send_notification,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _cond(campo: str, operador: str, valor: str, orden: int = 0) -> MagicMock:
    c = MagicMock()
    c.campo = campo
    c.operador = operador
    c.valor = valor
    c.orden = orden
    return c


def _make_lead(datos: dict = None) -> MagicMock:
    lead = MagicMock()
    lead.id = uuid.uuid4()
    lead.datos = datos or {}
    lead.lead_base_id = None
    return lead


# ─────────────────────────────────────────────────────────────────────────────
# Unit: _evaluate_conditions
# ─────────────────────────────────────────────────────────────────────────────

class TestEvaluateConditions:

    def test_no_conditions_returns_true(self):
        assert _evaluate_conditions([], {}) is True

    # equals
    def test_equals_passes(self):
        cond = _cond("estado", "equals", "activo")
        assert _evaluate_conditions([cond], {"estado": "activo"}) is True

    def test_equals_fails(self):
        cond = _cond("estado", "equals", "activo")
        assert _evaluate_conditions([cond], {"estado": "inactivo"}) is False

    def test_equals_missing_field_fails(self):
        cond = _cond("estado", "equals", "activo")
        assert _evaluate_conditions([cond], {}) is False

    # not_equals
    def test_not_equals_passes(self):
        cond = _cond("estado", "not_equals", "inactivo")
        assert _evaluate_conditions([cond], {"estado": "activo"}) is True

    def test_not_equals_fails(self):
        cond = _cond("estado", "not_equals", "inactivo")
        assert _evaluate_conditions([cond], {"estado": "inactivo"}) is False

    # contains
    def test_contains_passes(self):
        cond = _cond("nombre", "contains", "Juan")
        assert _evaluate_conditions([cond], {"nombre": "Juan Carlos"}) is True

    def test_contains_fails(self):
        cond = _cond("nombre", "contains", "Pedro")
        assert _evaluate_conditions([cond], {"nombre": "Juan Carlos"}) is False

    # not_contains
    def test_not_contains_passes(self):
        cond = _cond("nombre", "not_contains", "Pedro")
        assert _evaluate_conditions([cond], {"nombre": "Juan Carlos"}) is True

    def test_not_contains_fails(self):
        cond = _cond("nombre", "not_contains", "Juan")
        assert _evaluate_conditions([cond], {"nombre": "Juan Carlos"}) is False

    # greater_than
    def test_greater_than_passes(self):
        cond = _cond("score", "greater_than", "50")
        assert _evaluate_conditions([cond], {"score": "75"}) is True

    def test_greater_than_fails_equal(self):
        cond = _cond("score", "greater_than", "50")
        assert _evaluate_conditions([cond], {"score": "50"}) is False

    def test_greater_than_non_numeric_fails(self):
        cond = _cond("score", "greater_than", "50")
        assert _evaluate_conditions([cond], {"score": "abc"}) is False

    # less_than
    def test_less_than_passes(self):
        cond = _cond("score", "less_than", "50")
        assert _evaluate_conditions([cond], {"score": "25"}) is True

    def test_less_than_fails_equal(self):
        cond = _cond("score", "less_than", "50")
        assert _evaluate_conditions([cond], {"score": "50"}) is False

    # is_empty / is_not_empty
    def test_is_empty_passes(self):
        cond = _cond("telefono", "is_empty", "")
        assert _evaluate_conditions([cond], {"telefono": ""}) is True

    def test_is_empty_fails_when_has_value(self):
        cond = _cond("telefono", "is_empty", "")
        assert _evaluate_conditions([cond], {"telefono": "1234"}) is False

    def test_is_not_empty_passes(self):
        cond = _cond("telefono", "is_not_empty", "")
        assert _evaluate_conditions([cond], {"telefono": "1234"}) is True

    def test_is_not_empty_fails_when_empty(self):
        cond = _cond("telefono", "is_not_empty", "")
        assert _evaluate_conditions([cond], {"telefono": ""}) is False

    # Unknown operator
    def test_unknown_operator_fails(self):
        cond = _cond("estado", "magic_operator", "value")
        assert _evaluate_conditions([cond], {"estado": "value"}) is False

    # AND logic: multiple conditions
    def test_all_conditions_must_pass(self):
        cond1 = _cond("estado", "equals", "activo", orden=0)
        cond2 = _cond("score", "greater_than", "50", orden=1)
        # Both pass
        assert _evaluate_conditions([cond1, cond2], {"estado": "activo", "score": "75"}) is True
        # One fails
        assert _evaluate_conditions([cond1, cond2], {"estado": "activo", "score": "25"}) is False

    def test_conditions_evaluated_in_order(self):
        """Lower orden value is evaluated first."""
        cond_first = _cond("a", "equals", "x", orden=1)
        cond_second = _cond("b", "equals", "y", orden=2)
        datos = {"a": "x", "b": "y"}
        assert _evaluate_conditions([cond_second, cond_first], datos) is True


# ─────────────────────────────────────────────────────────────────────────────
# Unit: individual action handlers
# ─────────────────────────────────────────────────────────────────────────────

class TestActionUpdateField:

    def test_updates_field_on_lead(self):
        db = MagicMock()
        lead = _make_lead(datos={"nombre": "Juan"})
        config = {"campo": "estado", "valor": "contactado"}
        result = _action_update_field(db, config, lead)
        assert result["success"] is True
        assert lead.datos["estado"] == "contactado"
        db.flush.assert_called_once()

    def test_returns_error_when_no_lead(self):
        db = MagicMock()
        config = {"campo": "estado", "valor": "x"}
        result = _action_update_field(db, config, None)
        assert result.get("success") is not True
        assert "No lead" in result["detail"]

    def test_returns_error_when_no_campo(self):
        db = MagicMock()
        lead = _make_lead()
        result = _action_update_field(db, {}, lead)
        assert result.get("success") is not True

    def test_preserves_existing_fields(self):
        db = MagicMock()
        lead = _make_lead(datos={"nombre": "Juan", "email": "j@j.com"})
        _action_update_field(db, {"campo": "estado", "valor": "ok"}, lead)
        assert lead.datos["nombre"] == "Juan"
        assert lead.datos["email"] == "j@j.com"


class TestActionMoveToBase:

    def test_moves_lead_to_base(self):
        db = MagicMock()
        base = MagicMock()
        base.id = uuid.uuid4()
        base.nombre = "Base Destino"
        db.query.return_value.filter.return_value.first.return_value = base

        lead = _make_lead()
        config = {"base_id": str(base.id)}
        result = _action_move_to_base(db, config, lead)

        assert result["success"] is True
        assert lead.lead_base_id == base.id

    def test_returns_error_when_no_lead(self):
        db = MagicMock()
        result = _action_move_to_base(db, {"base_id": str(uuid.uuid4())}, None)
        assert result.get("success") is not True

    def test_returns_error_when_base_not_found(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        lead = _make_lead()
        result = _action_move_to_base(db, {"base_id": str(uuid.uuid4())}, lead)
        assert result.get("success") is not True
        assert "not found" in result["detail"]

    def test_returns_error_when_no_base_id_in_config(self):
        db = MagicMock()
        lead = _make_lead()
        result = _action_move_to_base(db, {}, lead)
        assert result.get("success") is not True


class TestActionSendNotification:

    def test_notification_always_succeeds(self):
        result = _action_send_notification(
            {"channel": "log", "message": "Test message"},
            {"lead_id": str(uuid.uuid4())},
        )
        assert result["success"] is True

    def test_uses_defaults_when_config_empty(self):
        result = _action_send_notification({}, {})
        assert result["success"] is True


# ─────────────────────────────────────────────────────────────────────────────
# Integration: run_automations with DB fixtures
# ─────────────────────────────────────────────────────────────────────────────

class TestRunAutomations:
    """Integration tests that hit the real test database."""

    def test_run_automations_no_automations_is_noop(
        self, db_session, test_account
    ):
        """Should not raise when there are no automations configured."""
        from app.services.automation_engine import run_automations
        from app.models.lead import Lead

        lead = Lead(cuenta_id=test_account.id, datos={"nombre": "Test"})
        db_session.add(lead)
        db_session.commit()

        # Should not raise
        run_automations(db_session, test_account.id, "lead_created", lead=lead)

    def test_run_automations_with_matching_automation(
        self, db_session, test_account
    ):
        """Automation with matching conditions should execute and be logged."""
        from app.services.automation_engine import run_automations
        from app.models.automation import Automation, AutomationCondition, AutomationAction, AutomationLog
        from app.models.lead import Lead

        lead = Lead(cuenta_id=test_account.id, datos={"estado": "nuevo"})
        db_session.add(lead)
        db_session.flush()

        auto = Automation(
            cuenta_id=test_account.id,
            nombre="Test Automation",
            trigger_tipo="lead_created",
            activo=True,
        )
        db_session.add(auto)
        db_session.flush()

        cond = AutomationCondition(
            automation_id=auto.id,
            campo="estado",
            operador="equals",
            valor="nuevo",
            orden=0,
        )
        db_session.add(cond)

        action = AutomationAction(
            automation_id=auto.id,
            tipo="update_field",
            config={"campo": "procesado", "valor": "si"},
            orden=0,
        )
        db_session.add(action)
        db_session.commit()

        run_automations(db_session, test_account.id, "lead_created", lead=lead)

        # Log should be created
        log = db_session.query(AutomationLog).filter(
            AutomationLog.automation_id == auto.id
        ).first()
        assert log is not None
        assert log.conditions_passed is True
        assert lead.datos.get("procesado") == "si"

    def test_run_automations_with_non_matching_conditions(
        self, db_session, test_account
    ):
        """Automation whose conditions don't pass should log but not execute actions."""
        from app.services.automation_engine import run_automations
        from app.models.automation import Automation, AutomationCondition, AutomationAction, AutomationLog
        from app.models.lead import Lead

        lead = Lead(cuenta_id=test_account.id, datos={"estado": "viejo"})
        db_session.add(lead)
        db_session.flush()

        auto = Automation(
            cuenta_id=test_account.id,
            nombre="Conditional Automation",
            trigger_tipo="lead_updated",
            activo=True,
        )
        db_session.add(auto)
        db_session.flush()

        cond = AutomationCondition(
            automation_id=auto.id,
            campo="estado",
            operador="equals",
            valor="nuevo",  # Lead has "viejo" → won't match
            orden=0,
        )
        db_session.add(cond)
        db_session.commit()

        run_automations(db_session, test_account.id, "lead_updated", lead=lead)

        log = db_session.query(AutomationLog).filter(
            AutomationLog.automation_id == auto.id
        ).first()
        assert log is not None
        assert log.conditions_passed is False
