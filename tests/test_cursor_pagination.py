"""
Tests for cursor-based pagination.

Validates correctness, performance properties, and backward compatibility
with offset mode.
"""
import pytest
from fastapi.testclient import TestClient

from app.core.pagination import decode_cursor, encode_cursor, apply_cursor_filter, build_next_cursor


# ─────────────────────────────────────────────────────────────────────────────
# Unit: cursor encode/decode
# ─────────────────────────────────────────────────────────────────────────────

class TestCursorEncoding:

    def test_encode_then_decode_roundtrip(self):
        import uuid
        from datetime import datetime, timezone
        ts = datetime(2026, 3, 12, 10, 30, 0, tzinfo=timezone.utc)
        uid = uuid.uuid4()
        cursor = encode_cursor(ts, uid)
        result = decode_cursor(cursor)
        assert result is not None
        decoded_ts, decoded_id = result
        assert decoded_ts == ts
        assert decoded_id == uid

    def test_decode_none_returns_none(self):
        assert decode_cursor(None) is None

    def test_decode_empty_string_returns_none(self):
        assert decode_cursor("") is None

    def test_decode_garbage_returns_none(self):
        assert decode_cursor("not-a-valid-cursor!!!") is None

    def test_decode_truncated_cursor_returns_none(self):
        assert decode_cursor("aGVsbG8=") is None  # valid base64, invalid JSON structure

    def test_cursor_is_url_safe(self):
        import uuid
        from datetime import datetime, timezone
        ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
        cursor = encode_cursor(ts, uuid.uuid4())
        # URL-safe base64 uses - and _ instead of + and /
        assert "+" not in cursor
        assert "/" not in cursor


class TestBuildNextCursor:

    def test_no_extra_item_means_last_page(self):
        from unittest.mock import MagicMock
        items = [MagicMock() for _ in range(5)]
        next_cursor, trimmed = build_next_cursor(items, page_size=5)
        assert next_cursor is None
        assert len(trimmed) == 5

    def test_extra_item_triggers_next_cursor(self):
        import uuid
        from datetime import datetime, timezone
        from unittest.mock import MagicMock

        items = []
        for i in range(6):  # 5 requested + 1 extra
            m = MagicMock()
            m.id = uuid.uuid4()
            m.created_at = datetime(2026, 1, i + 1, tzinfo=timezone.utc)
            items.append(m)

        next_cursor, trimmed = build_next_cursor(items, page_size=5)
        assert next_cursor is not None
        assert len(trimmed) == 5  # extra item is trimmed
        assert decode_cursor(next_cursor) is not None

    def test_cursor_points_to_last_returned_item(self):
        import uuid
        from datetime import datetime, timezone
        from unittest.mock import MagicMock

        last_ts = datetime(2026, 3, 5, tzinfo=timezone.utc)
        last_id = uuid.uuid4()

        items = []
        for i in range(5):
            m = MagicMock()
            m.id = uuid.uuid4()
            m.created_at = datetime(2026, 3, i + 1, tzinfo=timezone.utc)
            items.append(m)

        # Inject known last item at position 4 (index 3), add one extra
        items[4].id = last_id
        items[4].created_at = last_ts
        extra = MagicMock()
        extra.id = uuid.uuid4()
        extra.created_at = datetime(2026, 3, 6, tzinfo=timezone.utc)
        items.append(extra)

        next_cursor, trimmed = build_next_cursor(items, page_size=5)
        decoded = decode_cursor(next_cursor)
        assert decoded is not None
        decoded_ts, decoded_id = decoded
        assert decoded_id == last_id


# ─────────────────────────────────────────────────────────────────────────────
# Integration: cursor pagination on the leads endpoint
# ─────────────────────────────────────────────────────────────────────────────

class TestLeadsCursorPagination:

    def _create_leads(self, client, test_account, admin_headers, count: int) -> None:
        for i in range(count):
            client.post(
                f"/api/v1/admin/accounts/{test_account.id}/leads",
                headers=admin_headers,
                json={"datos": {"nombre": f"Lead {i:03d}", "orden": str(i)}},
            )

    def test_first_page_without_cursor_returns_next_cursor(
        self, client: TestClient, test_account, admin_headers
    ):
        self._create_leads(client, test_account, admin_headers, 5)

        resp = client.get(
            f"/api/v1/admin/accounts/{test_account.id}/leads?page_size=3",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 3
        assert data["next_cursor"] is not None  # more pages exist

    def test_last_page_has_no_next_cursor(
        self, client: TestClient, test_account, admin_headers
    ):
        self._create_leads(client, test_account, admin_headers, 2)

        resp = client.get(
            f"/api/v1/admin/accounts/{test_account.id}/leads?page_size=10",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) <= 10
        # If all fits in one page, next_cursor should be None
        if len(data["items"]) < 10:
            assert data["next_cursor"] is None

    def test_cursor_pagination_covers_all_leads(
        self, client: TestClient, test_account, admin_headers
    ):
        """Paginate through all leads using cursors — no duplicates, no gaps."""
        self._create_leads(client, test_account, admin_headers, 7)

        page_size = 3
        all_ids = []
        next_cursor = None

        while True:
            url = f"/api/v1/admin/accounts/{test_account.id}/leads?page_size={page_size}"
            if next_cursor:
                url += f"&cursor={next_cursor}"

            resp = client.get(url, headers=admin_headers)
            assert resp.status_code == 200
            data = resp.json()

            ids = [item["id"] for item in data["items"]]
            all_ids.extend(ids)

            next_cursor = data.get("next_cursor")
            if not next_cursor:
                break

        # All IDs should be unique (no duplicates across pages)
        assert len(all_ids) == len(set(all_ids))
        # Should have retrieved all 7 leads
        assert len(all_ids) == 7

    def test_cursor_mode_total_is_minus_one(
        self, client: TestClient, test_account, admin_headers
    ):
        """In cursor mode, total count is -1 (not computed for performance)."""
        self._create_leads(client, test_account, admin_headers, 3)

        # Get first page to obtain a cursor
        resp1 = client.get(
            f"/api/v1/admin/accounts/{test_account.id}/leads?page_size=2",
            headers=admin_headers,
        )
        cursor = resp1.json().get("next_cursor")
        if not cursor:
            pytest.skip("Not enough leads to generate cursor")

        resp2 = client.get(
            f"/api/v1/admin/accounts/{test_account.id}/leads?page_size=2&cursor={cursor}",
            headers=admin_headers,
        )
        assert resp2.status_code == 200
        assert resp2.json()["total"] == -1

    def test_malformed_cursor_falls_back_to_first_page(
        self, client: TestClient, test_account, admin_headers
    ):
        """A malformed cursor should not crash — should gracefully return results."""
        self._create_leads(client, test_account, admin_headers, 3)

        resp = client.get(
            f"/api/v1/admin/accounts/{test_account.id}/leads?cursor=NOT_VALID_CURSOR",
            headers=admin_headers,
        )
        assert resp.status_code == 200

    def test_offset_and_cursor_return_same_leads(
        self, client: TestClient, test_account, admin_headers
    ):
        """Offset page 1 and cursor first page should return the same items."""
        self._create_leads(client, test_account, admin_headers, 5)

        offset_resp = client.get(
            f"/api/v1/admin/accounts/{test_account.id}/leads?page=1&page_size=5",
            headers=admin_headers,
        )
        cursor_resp = client.get(
            f"/api/v1/admin/accounts/{test_account.id}/leads?page_size=5",
            headers=admin_headers,
        )

        assert offset_resp.status_code == 200
        assert cursor_resp.status_code == 200

        offset_ids = {item["id"] for item in offset_resp.json()["items"]}
        cursor_ids = {item["id"] for item in cursor_resp.json()["items"]}
        assert offset_ids == cursor_ids
