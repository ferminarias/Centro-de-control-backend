"""
Cursor-based pagination for large datasets (10M+ rows).

WHY cursor vs offset:
  OFFSET N skips N rows by scanning them — at 1M+ rows this is O(N) per page.
  A cursor uses a WHERE clause on an indexed column, making every page O(1).

STRATEGY:
  Cursor encodes the last item's (created_at, id) as an opaque base64 string.
  The query becomes:
      WHERE (created_at, id) < (cursor_created_at, cursor_id)   -- for DESC
  This is satisfied by the ix_leads_cuenta_created composite index.

BACKWARD COMPATIBILITY:
  If `cursor` param is None the endpoint falls back to offset pagination.
  Responses always include `next_cursor` (None when on last page).

USAGE:
    from app.core.pagination import decode_cursor, encode_cursor, CursorResult

    # In your endpoint:
    cursor_val = decode_cursor(cursor_param)   # → (datetime, UUID) | None
    query = apply_cursor_filter(query, cursor_val, Lead)
    items = query.limit(page_size + 1).all()
    next_cursor, items = build_next_cursor(items, page_size)
"""
import base64
import json
import uuid
from datetime import datetime, timezone
from typing import TypeVar

from sqlalchemy.orm import Query

T = TypeVar("T")

_SENTINEL = object()


# ─────────────────────────────────────────────────────────────────────────────
# Encode / decode
# ─────────────────────────────────────────────────────────────────────────────

def encode_cursor(created_at: datetime, row_id: uuid.UUID) -> str:
    """Encode a (created_at, id) pair into an opaque cursor string."""
    payload = {
        "ts": created_at.isoformat(),
        "id": str(row_id),
    }
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()


def decode_cursor(cursor: str | None) -> tuple[datetime, uuid.UUID] | None:
    """
    Decode an opaque cursor string back to (datetime, UUID).
    Returns None if cursor is None or malformed (graceful fallback to page 1).
    """
    if not cursor:
        return None
    try:
        raw = base64.urlsafe_b64decode(cursor.encode()).decode()
        payload = json.loads(raw)
        ts = datetime.fromisoformat(payload["ts"])
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return ts, uuid.UUID(payload["id"])
    except Exception:
        return None  # malformed cursor → treat as first page


# ─────────────────────────────────────────────────────────────────────────────
# Query helpers
# ─────────────────────────────────────────────────────────────────────────────

def apply_cursor_filter(query: Query, cursor_value: tuple | None, model) -> Query:
    """
    Add cursor WHERE clause to a query ordered DESC by (created_at, id).

    Produces:
        WHERE (created_at < cursor_ts)
           OR (created_at = cursor_ts AND id < cursor_id)

    This is equivalent to the row-value comparison:
        (created_at, id) < (cursor_ts, cursor_id)
    but expressed in a way that SQLAlchemy/PostgreSQL can use the composite index.
    """
    if cursor_value is None:
        return query
    cursor_ts, cursor_id = cursor_value
    return query.filter(
        (model.created_at < cursor_ts)
        | (
            (model.created_at == cursor_ts)
            & (model.id < cursor_id)
        )
    )


def build_next_cursor(items: list, page_size: int) -> tuple[str | None, list]:
    """
    Given `page_size + 1` fetched items, determine if there is a next page.

    Returns (next_cursor, trimmed_items).
    - next_cursor is None when we're on the last page.
    - trimmed_items has at most page_size items.
    """
    if len(items) > page_size:
        # There are more rows — the extra item tells us where to continue
        items = items[:page_size]
        last = items[-1]
        next_cursor = encode_cursor(last.created_at, last.id)
    else:
        next_cursor = None
    return next_cursor, items
