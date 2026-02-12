import re
from typing import Any

from app.models.field import FieldType

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^\+?\d[\d\s\-()]{6,}$")


def infer_type(value: Any) -> FieldType:
    """Infer the FieldType from a Python value."""
    if isinstance(value, bool):
        return FieldType.BOOLEAN
    if isinstance(value, (int, float)):
        return FieldType.NUMBER
    if not isinstance(value, str) or not value.strip():
        return FieldType.STRING

    val = value.strip()

    if EMAIL_RE.match(val):
        return FieldType.EMAIL
    if PHONE_RE.match(val):
        return FieldType.PHONE

    # Try numeric string
    try:
        float(val)
        return FieldType.NUMBER
    except ValueError:
        pass

    return FieldType.STRING
