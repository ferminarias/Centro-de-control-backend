"""
Unit tests for the scoring engine.
These are pure unit tests — no database required.
"""
import uuid
import pytest
from unittest.mock import MagicMock

from app.services.scoring_engine import calculate_score, recalculate_and_save


def _make_lead(**kwargs) -> MagicMock:
    """Build a mock Lead with sensible defaults."""
    lead = MagicMock()
    lead.datos = kwargs.pop("datos", {})
    lead.tipificacion_id = kwargs.pop("tipificacion_id", None)
    lead.subtipificacion_id = kwargs.pop("subtipificacion_id", None)
    lead.temperatura = kwargs.pop("temperatura", "frio")
    lead.assigned_to = kwargs.pop("assigned_to", None)
    lead.score = kwargs.pop("score", 0)
    for k, v in kwargs.items():
        setattr(lead, k, v)
    return lead


class TestCalculateScore:
    """Test score calculation logic without touching the database."""

    def test_empty_lead_scores_zero(self):
        lead = _make_lead()
        assert calculate_score(lead) == 0

    def test_email_adds_15_points(self):
        lead = _make_lead(datos={"email": "test@example.com"})
        assert calculate_score(lead) == 15

    def test_correo_alias_adds_15_points(self):
        lead = _make_lead(datos={"correo": "test@example.com"})
        assert calculate_score(lead) == 15

    def test_only_one_email_field_counted(self):
        """Having both email and correo should only add 15, not 30."""
        lead = _make_lead(datos={"email": "a@b.com", "correo": "c@d.com"})
        assert calculate_score(lead) == 15

    def test_phone_adds_15_points(self):
        lead = _make_lead(datos={"telefono": "+541155551234"})
        assert calculate_score(lead) == 15

    def test_phone_aliases_all_work(self):
        for field in ("phone", "tel", "celular", "movil"):
            lead = _make_lead(datos={field: "1234"})
            assert calculate_score(lead) == 15, f"Field '{field}' should add 15 pts"

    def test_nombre_adds_10_points(self):
        lead = _make_lead(datos={"nombre": "Juan"})
        assert calculate_score(lead) == 10

    def test_apellido_adds_5_points(self):
        lead = _make_lead(datos={"apellido": "Perez"})
        assert calculate_score(lead) == 5

    def test_tipificacion_adds_20_points(self):
        lead = _make_lead(tipificacion_id=uuid.uuid4())
        assert calculate_score(lead) == 20

    def test_subtipificacion_adds_10_points(self):
        lead = _make_lead(
            tipificacion_id=uuid.uuid4(),
            subtipificacion_id=uuid.uuid4(),
        )
        assert calculate_score(lead) == 30  # 20 + 10

    def test_temperatura_tibio_adds_8_points(self):
        lead = _make_lead(temperatura="tibio")
        assert calculate_score(lead) == 8

    def test_temperatura_caliente_adds_15_points(self):
        lead = _make_lead(temperatura="caliente")
        assert calculate_score(lead) == 15

    def test_temperatura_frio_adds_0_points(self):
        lead = _make_lead(temperatura="frio")
        assert calculate_score(lead) == 0

    def test_unknown_temperatura_adds_0_points(self):
        lead = _make_lead(temperatura="desconocido")
        assert calculate_score(lead) == 0

    def test_assigned_to_adds_10_points(self):
        lead = _make_lead(assigned_to=uuid.uuid4())
        assert calculate_score(lead) == 10

    def test_perfect_lead_scores_100(self):
        """A lead with all fields filled scores exactly 100."""
        lead = _make_lead(
            datos={
                "email": "full@example.com",
                "telefono": "+5411999",
                "nombre": "Juan",
                "apellido": "Perez",
            },
            tipificacion_id=uuid.uuid4(),
            subtipificacion_id=uuid.uuid4(),
            temperatura="caliente",
            assigned_to=uuid.uuid4(),
        )
        # 15+15+10+5+20+10+15+10 = 100
        assert calculate_score(lead) == 100

    def test_score_never_exceeds_100(self):
        """Score is capped at 100 even if all bonuses exceed it."""
        lead = _make_lead(
            datos={
                "email": "x@x.com",
                "correo": "y@y.com",  # second email, won't double-count
                "telefono": "111",
                "phone": "222",       # second phone, won't double-count
                "nombre": "N",
                "apellido": "A",
            },
            tipificacion_id=uuid.uuid4(),
            subtipificacion_id=uuid.uuid4(),
            temperatura="caliente",
            assigned_to=uuid.uuid4(),
        )
        assert calculate_score(lead) <= 100

    def test_empty_string_fields_dont_count(self):
        lead = _make_lead(datos={"email": "  ", "telefono": "", "nombre": ""})
        assert calculate_score(lead) == 0


class TestRecalculateAndSave:
    """Test that recalculate_and_save persists the new score when it changes."""

    def test_saves_new_score_when_different(self):
        db = MagicMock()
        lead = _make_lead(datos={"email": "a@b.com"}, score=0)
        new_score = recalculate_and_save(db, lead)
        assert new_score == 15
        assert lead.score == 15
        db.add.assert_called_once_with(lead)

    def test_does_not_save_when_score_unchanged(self):
        db = MagicMock()
        lead = _make_lead(datos={"email": "a@b.com"}, score=15)
        new_score = recalculate_and_save(db, lead)
        assert new_score == 15
        db.add.assert_not_called()
