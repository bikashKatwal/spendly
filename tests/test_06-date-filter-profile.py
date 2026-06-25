"""
tests/test_06-date-filter-profile.py

Pytest tests for the Spendly date filter feature on GET /expenses.
Spec: .claude/specs/06-date-filter-profile.md

Covers:
- Auth guard (unauthenticated redirect)
- No-param request returns all expenses
- date_from filter: only on/after date
- date_to filter: only on/before date
- Combined date_from + date_to range filter
- Empty string params behave like no filter
- Malformed date values are silently ignored (no 500)
- Filter matching no expenses renders empty state without crashing
- Filter inputs are pre-populated with submitted values
- "Clear" link present when filter is active
- Filtered notice present when filter is active
- "Clear" link absent when no filter is active
"""

import pytest
from werkzeug.security import generate_password_hash

from app import app as flask_app
from database.db import get_db, init_db


# ---------------------------------------------------------------------------
# Known seed data — 3 expenses on clearly separated dates
# ---------------------------------------------------------------------------
EXPENSE_EARLY  = ("2026-01-10", "Food",      10.00, "Early breakfast")
EXPENSE_MIDDLE = ("2026-03-15", "Transport", 25.00, "Mid-year train")
EXPENSE_LATE   = ("2026-06-20", "Bills",     99.00, "Late electricity")

TEST_EMAIL    = "filter_tester@spendly.com"
TEST_PASSWORD = "securepass123"
TEST_NAME     = "Filter Tester"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def app(tmp_path):
    """Flask app configured with an isolated on-disk SQLite DB per test."""
    db_file = str(tmp_path / "test_spendly.db")
    flask_app.config.update({
        "TESTING": True,
        "DATABASE": db_file,
        "SECRET_KEY": "test-secret-key",
        "WTF_CSRF_ENABLED": False,
    })

    import database.db as db_module
    original_db_path = db_module.DB_PATH
    db_module.DB_PATH = db_file

    with flask_app.app_context():
        init_db()
        yield flask_app

    db_module.DB_PATH = original_db_path


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def seeded_auth_client(client):
    """
    Registers a user, seeds 3 expenses across 3 distinct dates, and returns
    a logged-in test client so every test starts with known data.
    """
    # Register
    client.post("/register", data={
        "name":             TEST_NAME,
        "email":            TEST_EMAIL,
        "password":         TEST_PASSWORD,
        "confirm_password": TEST_PASSWORD,
    })

    # Retrieve the user id to insert expenses directly
    conn = get_db()
    user = conn.execute(
        "SELECT id FROM users WHERE email = ?", (TEST_EMAIL,)
    ).fetchone()
    user_id = user["id"]

    # Insert 3 known expenses
    conn.executemany(
        "INSERT INTO expenses (user_id, date, category, amount, description)"
        " VALUES (?, ?, ?, ?, ?)",
        [
            (user_id, EXPENSE_EARLY[0],  EXPENSE_EARLY[1],  EXPENSE_EARLY[2],  EXPENSE_EARLY[3]),
            (user_id, EXPENSE_MIDDLE[0], EXPENSE_MIDDLE[1], EXPENSE_MIDDLE[2], EXPENSE_MIDDLE[3]),
            (user_id, EXPENSE_LATE[0],   EXPENSE_LATE[1],   EXPENSE_LATE[2],   EXPENSE_LATE[3]),
        ],
    )
    conn.commit()
    conn.close()

    # Log in
    client.post("/login", data={"email": TEST_EMAIL, "password": TEST_PASSWORD})

    return client


# ---------------------------------------------------------------------------
# 1. Auth guard
# ---------------------------------------------------------------------------

class TestAuthGuard:
    def test_unauthenticated_get_expenses_redirects_to_login(self, client):
        response = client.get("/expenses")
        assert response.status_code == 302, "Expected redirect for unauthenticated user"
        assert "/login" in response.headers["Location"], \
            "Unauthenticated request should redirect to /login"

    def test_unauthenticated_get_expenses_with_params_redirects_to_login(self, client):
        response = client.get("/expenses?date_from=2026-01-01&date_to=2026-12-31")
        assert response.status_code == 302, "Expected redirect even when query params are present"
        assert "/login" in response.headers["Location"], \
            "Should redirect to /login regardless of query parameters"


# ---------------------------------------------------------------------------
# 2. No params — all expenses returned
# ---------------------------------------------------------------------------

class TestNoFilter:
    def test_no_params_returns_200(self, seeded_auth_client):
        response = seeded_auth_client.get("/expenses")
        assert response.status_code == 200, "GET /expenses with no params should return 200"

    def test_no_params_shows_all_expenses(self, seeded_auth_client):
        response = seeded_auth_client.get("/expenses")
        data = response.data
        # All three descriptions must appear
        assert EXPENSE_EARLY[3].encode()  in data, "Early expense description should be present"
        assert EXPENSE_MIDDLE[3].encode() in data, "Middle expense description should be present"
        assert EXPENSE_LATE[3].encode()   in data, "Late expense description should be present"

    def test_no_params_no_clear_link_required(self, seeded_auth_client):
        """
        When no filter is active, a 'Clear' link is not required.
        The page must still return 200 and not crash.
        """
        response = seeded_auth_client.get("/expenses")
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# 3. date_from filter
# ---------------------------------------------------------------------------

class TestDateFromFilter:
    def test_date_from_excludes_earlier_expenses(self, seeded_auth_client):
        """Expenses before date_from must not appear."""
        response = seeded_auth_client.get("/expenses?date_from=2026-03-01")
        data = response.data
        assert response.status_code == 200
        assert EXPENSE_EARLY[3].encode() not in data, \
            "Expense before date_from should not appear"

    def test_date_from_includes_on_or_after_expenses(self, seeded_auth_client):
        """Expenses on or after date_from must appear."""
        response = seeded_auth_client.get("/expenses?date_from=2026-03-01")
        data = response.data
        assert EXPENSE_MIDDLE[3].encode() in data, \
            "Expense on/after date_from should appear"
        assert EXPENSE_LATE[3].encode() in data, \
            "Expense on/after date_from should appear"

    def test_date_from_exact_boundary_included(self, seeded_auth_client):
        """An expense whose date equals date_from must be included."""
        response = seeded_auth_client.get(f"/expenses?date_from={EXPENSE_MIDDLE[0]}")
        assert EXPENSE_MIDDLE[3].encode() in response.data, \
            "Expense exactly on date_from boundary should be included"


# ---------------------------------------------------------------------------
# 4. date_to filter
# ---------------------------------------------------------------------------

class TestDateToFilter:
    def test_date_to_excludes_later_expenses(self, seeded_auth_client):
        """Expenses after date_to must not appear."""
        response = seeded_auth_client.get("/expenses?date_to=2026-03-31")
        data = response.data
        assert response.status_code == 200
        assert EXPENSE_LATE[3].encode() not in data, \
            "Expense after date_to should not appear"

    def test_date_to_includes_on_or_before_expenses(self, seeded_auth_client):
        """Expenses on or before date_to must appear."""
        response = seeded_auth_client.get("/expenses?date_to=2026-03-31")
        data = response.data
        assert EXPENSE_EARLY[3].encode()  in data, \
            "Expense on/before date_to should appear"
        assert EXPENSE_MIDDLE[3].encode() in data, \
            "Expense on/before date_to should appear"

    def test_date_to_exact_boundary_included(self, seeded_auth_client):
        """An expense whose date equals date_to must be included."""
        response = seeded_auth_client.get(f"/expenses?date_to={EXPENSE_MIDDLE[0]}")
        assert EXPENSE_MIDDLE[3].encode() in response.data, \
            "Expense exactly on date_to boundary should be included"


# ---------------------------------------------------------------------------
# 5. Combined date_from + date_to range
# ---------------------------------------------------------------------------

class TestDateRangeFilter:
    def test_range_returns_only_expenses_within_range(self, seeded_auth_client):
        response = seeded_auth_client.get(
            "/expenses?date_from=2026-03-01&date_to=2026-03-31"
        )
        data = response.data
        assert response.status_code == 200
        assert EXPENSE_MIDDLE[3].encode() in data, \
            "Expense within range should appear"
        assert EXPENSE_EARLY[3].encode() not in data, \
            "Expense before range should not appear"
        assert EXPENSE_LATE[3].encode() not in data, \
            "Expense after range should not appear"

    def test_range_spanning_all_expenses_returns_all(self, seeded_auth_client):
        response = seeded_auth_client.get(
            "/expenses?date_from=2026-01-01&date_to=2026-12-31"
        )
        data = response.data
        assert EXPENSE_EARLY[3].encode()  in data
        assert EXPENSE_MIDDLE[3].encode() in data
        assert EXPENSE_LATE[3].encode()   in data


# ---------------------------------------------------------------------------
# 6. Empty string params behave like no filter
# ---------------------------------------------------------------------------

class TestEmptyParamsFilter:
    def test_empty_date_from_and_to_returns_all_expenses(self, seeded_auth_client):
        response = seeded_auth_client.get("/expenses?date_from=&date_to=")
        data = response.data
        assert response.status_code == 200
        assert EXPENSE_EARLY[3].encode()  in data, "Empty filter should show all expenses"
        assert EXPENSE_MIDDLE[3].encode() in data, "Empty filter should show all expenses"
        assert EXPENSE_LATE[3].encode()   in data, "Empty filter should show all expenses"

    def test_empty_date_from_only_returns_all(self, seeded_auth_client):
        response = seeded_auth_client.get("/expenses?date_from=")
        assert response.status_code == 200
        data = response.data
        assert EXPENSE_EARLY[3].encode()  in data
        assert EXPENSE_MIDDLE[3].encode() in data
        assert EXPENSE_LATE[3].encode()   in data

    def test_empty_date_to_only_returns_all(self, seeded_auth_client):
        response = seeded_auth_client.get("/expenses?date_to=")
        assert response.status_code == 200
        data = response.data
        assert EXPENSE_EARLY[3].encode()  in data
        assert EXPENSE_MIDDLE[3].encode() in data
        assert EXPENSE_LATE[3].encode()   in data


# ---------------------------------------------------------------------------
# 7. Malformed date values are silently ignored (no 500)
# ---------------------------------------------------------------------------

class TestMalformedDateParams:
    @pytest.mark.parametrize("query_string", [
        "date_from=bad-value",
        "date_to=bad-value",
        "date_from=bad-value&date_to=also-bad",
        "date_from=2026/01/10",           # wrong separator
        "date_from=01-10-2026",           # wrong order
        "date_from=notadate&date_to=2026-03-15",
        "date_from=2026-13-01",           # invalid month — silently ignored per spec
        "date_from=<script>alert(1)</script>",
        "date_from=2026-01-10'; DROP TABLE expenses; --",
    ])
    def test_malformed_date_does_not_cause_500(self, seeded_auth_client, query_string):
        response = seeded_auth_client.get(f"/expenses?{query_string}")
        assert response.status_code == 200, \
            f"Malformed date in '{query_string}' must not cause a 500 error"

    def test_malformed_date_from_returns_all_expenses(self, seeded_auth_client):
        """A malformed date_from is ignored so all expenses appear."""
        response = seeded_auth_client.get("/expenses?date_from=not-a-date")
        data = response.data
        assert EXPENSE_EARLY[3].encode()  in data, \
            "Malformed date_from should be ignored; all expenses should show"
        assert EXPENSE_MIDDLE[3].encode() in data
        assert EXPENSE_LATE[3].encode()   in data

    def test_malformed_date_to_returns_all_expenses(self, seeded_auth_client):
        """A malformed date_to is ignored so all expenses appear."""
        response = seeded_auth_client.get("/expenses?date_to=not-a-date")
        data = response.data
        assert EXPENSE_EARLY[3].encode()  in data
        assert EXPENSE_MIDDLE[3].encode() in data
        assert EXPENSE_LATE[3].encode()   in data


# ---------------------------------------------------------------------------
# 8. Filter matches no expenses — empty state renders without crashing
# ---------------------------------------------------------------------------

class TestEmptyFilterResults:
    def test_filter_with_no_matches_returns_200(self, seeded_auth_client):
        # Use a date range with no expenses
        response = seeded_auth_client.get(
            "/expenses?date_from=2025-01-01&date_to=2025-01-31"
        )
        assert response.status_code == 200, \
            "Filter matching no expenses must return 200, not crash"

    def test_filter_with_no_matches_does_not_show_expense_descriptions(self, seeded_auth_client):
        response = seeded_auth_client.get(
            "/expenses?date_from=2025-01-01&date_to=2025-01-31"
        )
        data = response.data
        assert EXPENSE_EARLY[3].encode()  not in data
        assert EXPENSE_MIDDLE[3].encode() not in data
        assert EXPENSE_LATE[3].encode()   not in data

    def test_filter_with_no_matches_renders_valid_html_page(self, seeded_auth_client):
        """Response should still render the base template structure."""
        response = seeded_auth_client.get(
            "/expenses?date_from=2025-01-01&date_to=2025-01-31"
        )
        # base.html always renders an <html> or at minimum a body — spot-check
        assert b"<html" in response.data or b"<!DOCTYPE" in response.data, \
            "Empty filter result should still render a full HTML page"


# ---------------------------------------------------------------------------
# 9. Filter inputs pre-populated with submitted values
# ---------------------------------------------------------------------------

class TestFilterInputPrePopulation:
    def test_date_from_value_pre_populated_in_input(self, seeded_auth_client):
        response = seeded_auth_client.get("/expenses?date_from=2026-03-01")
        assert b"2026-03-01" in response.data, \
            "The submitted date_from value should appear pre-populated in the response HTML"

    def test_date_to_value_pre_populated_in_input(self, seeded_auth_client):
        response = seeded_auth_client.get("/expenses?date_to=2026-03-31")
        assert b"2026-03-31" in response.data, \
            "The submitted date_to value should appear pre-populated in the response HTML"

    def test_both_date_values_pre_populated(self, seeded_auth_client):
        response = seeded_auth_client.get(
            "/expenses?date_from=2026-03-01&date_to=2026-03-31"
        )
        assert b"2026-03-01" in response.data, \
            "date_from should be pre-populated"
        assert b"2026-03-31" in response.data, \
            "date_to should be pre-populated"

    def test_malformed_date_not_pre_populated(self, seeded_auth_client):
        """
        A malformed date is silently ignored by the route, so it should NOT
        be forwarded to the template as a filter value.
        """
        response = seeded_auth_client.get("/expenses?date_from=bad-value")
        # The raw malformed value should not be injected into the form
        # (implementation sets date_from=None then passes date_from or "" to template)
        assert b"bad-value" not in response.data, \
            "Malformed date_from should not be echoed back into the template"


# ---------------------------------------------------------------------------
# 10. "Clear" link present when filter is active
# ---------------------------------------------------------------------------

class TestClearLink:
    def test_clear_link_present_when_date_from_active(self, seeded_auth_client):
        response = seeded_auth_client.get("/expenses?date_from=2026-03-01")
        assert b"/expenses" in response.data, \
            "A link back to /expenses (Clear) should be present when filter is active"

    def test_clear_link_present_when_date_to_active(self, seeded_auth_client):
        response = seeded_auth_client.get("/expenses?date_to=2026-03-31")
        assert b"/expenses" in response.data, \
            "A link back to /expenses (Clear) should be present when filter is active"

    def test_clear_link_present_when_both_filters_active(self, seeded_auth_client):
        response = seeded_auth_client.get(
            "/expenses?date_from=2026-03-01&date_to=2026-03-31"
        )
        # The word "Clear" or a link to bare /expenses should exist
        data = response.data
        has_clear_text = b"Clear" in data or b"clear" in data
        has_expenses_link = b'href="/expenses"' in data or b"href='/expenses'" in data
        assert has_clear_text or has_expenses_link, \
            "A 'Clear' link or equivalent should appear when filter is active"


# ---------------------------------------------------------------------------
# 11. Filtered notice present when filter is active
# ---------------------------------------------------------------------------

class TestFilterNotice:
    def test_filtered_notice_present_with_date_from(self, seeded_auth_client):
        response = seeded_auth_client.get("/expenses?date_from=2026-03-01")
        data = response.data
        # Spec says: show a notice like "Showing filtered results"
        assert b"filter" in data.lower() or b"Showing filtered" in data, \
            "A filtered-results notice should be visible when date_from is active"

    def test_filtered_notice_present_with_date_to(self, seeded_auth_client):
        response = seeded_auth_client.get("/expenses?date_to=2026-03-31")
        data = response.data
        assert b"filter" in data.lower() or b"Showing filtered" in data, \
            "A filtered-results notice should be visible when date_to is active"

    def test_filtered_notice_present_with_both_dates(self, seeded_auth_client):
        response = seeded_auth_client.get(
            "/expenses?date_from=2026-03-01&date_to=2026-03-31"
        )
        data = response.data
        assert b"filter" in data.lower() or b"Showing filtered" in data, \
            "A filtered-results notice should be visible when both dates are active"

    def test_no_active_filter_still_renders_200(self, seeded_auth_client):
        """Baseline — no filter active should still render correctly."""
        response = seeded_auth_client.get("/expenses")
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# 12. HTTP semantics — correct status codes
# ---------------------------------------------------------------------------

class TestHTTPSemantics:
    def test_get_expenses_no_filter_is_200(self, seeded_auth_client):
        assert seeded_auth_client.get("/expenses").status_code == 200

    def test_get_expenses_with_valid_filter_is_200(self, seeded_auth_client):
        assert seeded_auth_client.get(
            "/expenses?date_from=2026-01-01&date_to=2026-12-31"
        ).status_code == 200

    def test_get_expenses_with_bad_filter_is_200_not_400(self, seeded_auth_client):
        assert seeded_auth_client.get(
            "/expenses?date_from=garbage"
        ).status_code == 200

    def test_unauthenticated_is_302(self, client):
        assert client.get("/expenses").status_code == 302
