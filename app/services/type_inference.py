import re
from typing import Any

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^\+?\d[\d\s\-()]{6,}$")


def infer_type(value: Any) -> str:
    """Infer the field type from a Python value. Returns lowercase string."""
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if not isinstance(value, str) or not value.strip():
        return "string"

    val = value.strip()

    if EMAIL_RE.match(val):
        return "email"
    if PHONE_RE.match(val):
        return "phone"

    try:
        float(val)
        return "number"
    except ValueError:
        pass

    return "string"
