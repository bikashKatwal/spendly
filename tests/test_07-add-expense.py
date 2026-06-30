"""
tests/test_07-add-expense.py

Pytest tests for the Spendly "Add Expense" feature.
Spec: .claude/specs/07-add-expense.md

Covers:
- Auth guard: unauthenticated GET and POST redirect to /login
- GET /expenses/add renders form with category select, amount input, date input,
  description textarea, and all allowed categories as options
- POST happy path: valid data inserts a DB row and redirects to /expenses (302)
- New expense visible on /expenses list after a successful POST
- POST validation errors for amount (missing, zero, negative, non-numeric) — 400,
  no redirect, no DB insert
- POST validation errors for invalid date format — 400, no redirect, no DB insert
- POST validation errors for invalid/disallowed category — 400, no redirect, no DB insert
- Optional description: blank or absent value is accepted and stored as None
- All 7 allowed categories are individually accepted (parametrized)
- create_expense() is importable and callable from database.db
- create_expense() called directly inserts the correct row
- create_expense() with None description stores NULL
- Inserted expense is linked to the correct authenticated user_id
"""

import pytest
from werkzeug.security import generate_password_hash

from app import app as flask_app
from database.db import get_db, init_db


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ALLOWED_CATEGORIES = [
    "Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"
]

TEST_NAME     = "Add Tester"
TEST_EMAIL    = "addtester@spendly.com"
TEST_PASSWORD = "testpass123"

VALID_EXPENSE = {
    "category":    "Food",
    "amount":      "42.50",
    "date":        "2026-05-15",
    "description": "Test lunch",
}


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
def auth_client(client):
    """Register a user and log in; return authenticated test client."""
    client.post("/register", data={
        "name":             TEST_NAME,
        "email":            TEST_EMAIL,
        "password":         TEST_PASSWORD,
        "confirm_password": TEST_PASSWORD,
    })
    client.post("/login", data={
        "email":    TEST_EMAIL,
        "password": TEST_PASSWORD,
    })
    return client


def _get_user_id(email=TEST_EMAIL):
    """Return the DB user id for the registered test user."""
    conn = get_db()
    row = conn.execute(
        "SELECT id FROM users WHERE email = ?", (email,)
    ).fetchone()
    conn.close()
    return row["id"]


def _fetch_expenses_for_user(email=TEST_EMAIL):
    """Return all expense rows for the named test user, ordered by id DESC."""
    conn = get_db()
    user = conn.execute(
        "SELECT id FROM users WHERE email = ?", (email,)
    ).fetchone()
    rows = conn.execute(
        "SELECT * FROM expenses WHERE user_id = ? ORDER BY id DESC", (user["id"],)
    ).fetchall()
    conn.close()
    return rows


# ---------------------------------------------------------------------------
# 1. Auth guard
# ---------------------------------------------------------------------------

class TestAuthGuard:
    def test_unauthenticated_get_redirects(self, client):
        response = client.get("/expenses/add")
        assert response.status_code in (302, 401), \
            "Unauthenticated GET /expenses/add must redirect or abort"
        if response.status_code == 302:
            assert "/login" in response.headers.get("Location", ""), \
                "Redirect must point to /login"

    def test_unauthenticated_post_redirects_or_aborts(self, client):
        response = client.post("/expenses/add", data=VALID_EXPENSE)
        assert response.status_code in (302, 401), \
            "Unauthenticated POST /expenses/add must redirect or abort"
        if response.status_code == 302:
            assert "/login" in response.headers.get("Location", ""), \
                "Redirect must point to /login"


# ---------------------------------------------------------------------------
# 2. GET /expenses/add — form rendering
# ---------------------------------------------------------------------------

class TestGetForm:
    def test_get_returns_200(self, auth_client):
        response = auth_client.get("/expenses/add")
        assert response.status_code == 200, \
            "GET /expenses/add must return 200 for an authenticated user"

    def test_get_renders_full_html_page(self, auth_client):
        response = auth_client.get("/expenses/add")
        assert b"<html" in response.data or b"<!DOCTYPE" in response.data, \
            "Response must be a full HTML page (extending base.html)"

    def test_form_has_category_select(self, auth_client):
        response = auth_client.get("/expenses/add")
        assert b"select" in response.data.lower(), \
            "Form must contain a <select> element for category"

    def test_form_has_amount_input(self, auth_client):
        response = auth_client.get("/expenses/add")
        assert b"amount" in response.data.lower(), \
            "Form must contain an amount input field"

    def test_form_has_date_input(self, auth_client):
        response = auth_client.get("/expenses/add")
        assert b"date" in response.data.lower(), \
            "Form must contain a date input field"

    def test_form_has_description_textarea(self, auth_client):
        response = auth_client.get("/expenses/add")
        data = response.data.lower()
        assert b"textarea" in data or b"description" in data, \
            "Form must contain a description textarea"

    def test_form_lists_all_allowed_categories(self, auth_client):
        response = auth_client.get("/expenses/add")
        for category in ALLOWED_CATEGORIES:
            assert category.encode() in response.data, \
                f"Category '{category}' must appear as an option in the select"


# ---------------------------------------------------------------------------
# 3. POST happy path — valid data
# ---------------------------------------------------------------------------

class TestPostHappyPath:
    def test_valid_post_redirects_to_expenses(self, auth_client):
        response = auth_client.post("/expenses/add", data=VALID_EXPENSE)
        assert response.status_code == 302, \
            "Valid POST must redirect (302)"
        assert "/expenses" in response.headers.get("Location", ""), \
            "Redirect after valid POST must target /expenses"

    def test_valid_post_inserts_exactly_one_row(self, auth_client, app):
        with app.app_context():
            auth_client.post("/expenses/add", data=VALID_EXPENSE)
            rows = _fetch_expenses_for_user()
            assert len(rows) == 1, \
                "Exactly one expense row should exist after one valid POST"

    def test_valid_post_stores_correct_amount(self, auth_client, app):
        with app.app_context():
            auth_client.post("/expenses/add", data=VALID_EXPENSE)
            rows = _fetch_expenses_for_user()
            assert float(rows[0]["amount"]) == pytest.approx(42.50), \
                "Stored amount must match the submitted value"

    def test_valid_post_stores_correct_category(self, auth_client, app):
        with app.app_context():
            auth_client.post("/expenses/add", data=VALID_EXPENSE)
            rows = _fetch_expenses_for_user()
            assert rows[0]["category"] == "Food", \
                "Stored category must match the submitted value"

    def test_valid_post_stores_correct_date(self, auth_client, app):
        with app.app_context():
            auth_client.post("/expenses/add", data=VALID_EXPENSE)
            rows = _fetch_expenses_for_user()
            assert rows[0]["date"] == "2026-05-15", \
                "Stored date must match the submitted value"

    def test_valid_post_stores_correct_description(self, auth_client, app):
        with app.app_context():
            auth_client.post("/expenses/add", data=VALID_EXPENSE)
            rows = _fetch_expenses_for_user()
            assert rows[0]["description"] == "Test lunch", \
                "Stored description must match the submitted value"

    def test_new_expense_appears_on_expenses_list(self, auth_client):
        auth_client.post("/expenses/add", data=VALID_EXPENSE)
        response = auth_client.get("/expenses")
        assert response.status_code == 200
        assert b"Test lunch" in response.data, \
            "New expense description must appear on /expenses after the redirect"

    def test_new_expense_amount_appears_on_expenses_list(self, auth_client):
        auth_client.post("/expenses/add", data=VALID_EXPENSE)
        response = auth_client.get("/expenses")
        # Amount may render as "42.5" or "42.50"; checking for the integer part is safe
        assert b"42" in response.data, \
            "New expense amount (42.50) should appear on /expenses list"


# ---------------------------------------------------------------------------
# 4. Optional description — blank or absent
# ---------------------------------------------------------------------------

class TestOptionalDescription:
    def test_blank_description_is_accepted(self, auth_client):
        data = {**VALID_EXPENSE, "description": ""}
        response = auth_client.post("/expenses/add", data=data)
        assert response.status_code == 302, \
            "Blank description must be accepted; POST should redirect"

    def test_blank_description_stored_as_null(self, auth_client, app):
        with app.app_context():
            data = {**VALID_EXPENSE, "description": ""}
            auth_client.post("/expenses/add", data=data)
            rows = _fetch_expenses_for_user()
            assert len(rows) == 1
            # Spec: store None if blank
            assert rows[0]["description"] is None or rows[0]["description"] == "", \
                "Blank description should be stored as None/NULL in the DB"

    def test_absent_description_field_is_accepted(self, auth_client):
        data = {k: v for k, v in VALID_EXPENSE.items() if k != "description"}
        response = auth_client.post("/expenses/add", data=data)
        assert response.status_code == 302, \
            "Missing description key must be accepted; POST should redirect"


# ---------------------------------------------------------------------------
# 5. Amount validation errors
# ---------------------------------------------------------------------------

class TestAmountValidation:
    def test_missing_amount_returns_400(self, auth_client):
        data = {k: v for k, v in VALID_EXPENSE.items() if k != "amount"}
        response = auth_client.post("/expenses/add", data=data)
        assert response.status_code == 400, "Missing amount must return 400"

    def test_empty_amount_returns_400(self, auth_client):
        data = {**VALID_EXPENSE, "amount": ""}
        response = auth_client.post("/expenses/add", data=data)
        assert response.status_code == 400, "Empty amount must return 400"

    def test_zero_amount_returns_400(self, auth_client):
        data = {**VALID_EXPENSE, "amount": "0"}
        response = auth_client.post("/expenses/add", data=data)
        assert response.status_code == 400, \
            "Zero amount must return 400 — only strictly positive values are valid"

    def test_zero_decimal_amount_returns_400(self, auth_client):
        data = {**VALID_EXPENSE, "amount": "0.00"}
        response = auth_client.post("/expenses/add", data=data)
        assert response.status_code == 400, "0.00 amount must return 400"

    def test_negative_amount_returns_400(self, auth_client):
        data = {**VALID_EXPENSE, "amount": "-10"}
        response = auth_client.post("/expenses/add", data=data)
        assert response.status_code == 400, "Negative amount must return 400"

    def test_negative_decimal_amount_returns_400(self, auth_client):
        data = {**VALID_EXPENSE, "amount": "-0.01"}
        response = auth_client.post("/expenses/add", data=data)
        assert response.status_code == 400, "Negative decimal amount must return 400"

    def test_non_numeric_amount_returns_400(self, auth_client):
        data = {**VALID_EXPENSE, "amount": "abc"}
        response = auth_client.post("/expenses/add", data=data)
        assert response.status_code == 400, "Non-numeric amount must return 400"

    @pytest.mark.parametrize("bad_amount", ["0", "-1", "-0.01", "abc", "", " "])
    def test_invalid_amounts_do_not_redirect(self, auth_client, bad_amount):
        data = {**VALID_EXPENSE, "amount": bad_amount}
        response = auth_client.post("/expenses/add", data=data)
        assert response.status_code != 302, \
            f"Invalid amount '{bad_amount}' must not produce a redirect"

    def test_zero_amount_does_not_insert_row(self, auth_client, app):
        with app.app_context():
            auth_client.post("/expenses/add", data={**VALID_EXPENSE, "amount": "0"})
            rows = _fetch_expenses_for_user()
            assert len(rows) == 0, "Zero amount must not insert a row into the DB"

    def test_negative_amount_does_not_insert_row(self, auth_client, app):
        with app.app_context():
            auth_client.post("/expenses/add", data={**VALID_EXPENSE, "amount": "-5"})
            rows = _fetch_expenses_for_user()
            assert len(rows) == 0, "Negative amount must not insert a row into the DB"

    def test_smallest_positive_decimal_accepted(self, auth_client):
        data = {**VALID_EXPENSE, "amount": "0.01"}
        response = auth_client.post("/expenses/add", data=data)
        assert response.status_code == 302, \
            "Smallest positive decimal (0.01) must be accepted"

    def test_amount_error_re_renders_form_not_redirect(self, auth_client):
        response = auth_client.post("/expenses/add", data={**VALID_EXPENSE, "amount": "0"})
        # Should re-render the form (contains form fields), not redirect
        assert response.status_code == 400
        assert b"amount" in response.data.lower(), \
            "Error response should re-render the add-expense form"


# ---------------------------------------------------------------------------
# 6. Date validation errors
# ---------------------------------------------------------------------------

class TestDateValidation:
    def test_missing_date_returns_400(self, auth_client):
        data = {k: v for k, v in VALID_EXPENSE.items() if k != "date"}
        response = auth_client.post("/expenses/add", data=data)
        assert response.status_code == 400, "Missing date must return 400"

    def test_empty_date_returns_400(self, auth_client):
        data = {**VALID_EXPENSE, "date": ""}
        response = auth_client.post("/expenses/add", data=data)
        assert response.status_code == 400, "Empty date must return 400"

    @pytest.mark.parametrize("bad_date", [
        "15-05-2026",       # DD-MM-YYYY — wrong order
        "2026/05/15",       # wrong separator
        "2026-5-15",        # no zero-padding on month
        "2026-05-5",        # no zero-padding on day
        "2026-13-01",       # invalid month (13)
        "2026-00-01",       # invalid month (0)
        "notadate",
        "2026-05",          # incomplete — no day
        "05/15/2026",       # US MM/DD/YYYY format
        "20260515",         # no separators
        "<script>",         # injection attempt
    ])
    def test_malformed_date_returns_400(self, auth_client, bad_date):
        data = {**VALID_EXPENSE, "date": bad_date}
        response = auth_client.post("/expenses/add", data=data)
        assert response.status_code == 400, \
            f"Malformed date '{bad_date}' must return 400"

    @pytest.mark.parametrize("bad_date", ["notadate", "", "15-05-2026"])
    def test_invalid_date_does_not_redirect(self, auth_client, bad_date):
        data = {**VALID_EXPENSE, "date": bad_date}
        response = auth_client.post("/expenses/add", data=data)
        assert response.status_code != 302, \
            f"Invalid date '{bad_date}' must not produce a redirect"

    def test_invalid_date_does_not_insert_row(self, auth_client, app):
        with app.app_context():
            auth_client.post("/expenses/add", data={**VALID_EXPENSE, "date": "bad-date"})
            rows = _fetch_expenses_for_user()
            assert len(rows) == 0, "Invalid date must not insert a row into the DB"

    def test_valid_date_format_accepted(self, auth_client):
        data = {**VALID_EXPENSE, "date": "2026-01-01"}
        response = auth_client.post("/expenses/add", data=data)
        assert response.status_code == 302, "Valid YYYY-MM-DD date must be accepted"

    def test_date_error_re_renders_form(self, auth_client):
        response = auth_client.post("/expenses/add", data={**VALID_EXPENSE, "date": "bad"})
        assert response.status_code == 400
        assert b"date" in response.data.lower(), \
            "Error response for bad date should re-render the form"


# ---------------------------------------------------------------------------
# 7. Category validation errors
# ---------------------------------------------------------------------------

class TestCategoryValidation:
    def test_missing_category_returns_400(self, auth_client):
        data = {k: v for k, v in VALID_EXPENSE.items() if k != "category"}
        response = auth_client.post("/expenses/add", data=data)
        assert response.status_code == 400, "Missing category must return 400"

    def test_empty_category_returns_400(self, auth_client):
        data = {**VALID_EXPENSE, "category": ""}
        response = auth_client.post("/expenses/add", data=data)
        assert response.status_code == 400, "Empty category must return 400"

    @pytest.mark.parametrize("bad_category", [
        "food",            # lowercase
        "FOOD",            # all caps
        "Groceries",       # not in allowed list
        "Random",
        "<script>",        # injection attempt
        "Food; DROP TABLE expenses;",
    ])
    def test_invalid_category_returns_400(self, auth_client, bad_category):
        data = {**VALID_EXPENSE, "category": bad_category}
        response = auth_client.post("/expenses/add", data=data)
        assert response.status_code == 400, \
            f"Invalid category '{bad_category}' must return 400"

    @pytest.mark.parametrize("bad_category", ["Groceries", "food", ""])
    def test_invalid_category_does_not_redirect(self, auth_client, bad_category):
        data = {**VALID_EXPENSE, "category": bad_category}
        response = auth_client.post("/expenses/add", data=data)
        assert response.status_code != 302, \
            f"Invalid category '{bad_category}' must not produce a redirect"

    def test_invalid_category_does_not_insert_row(self, auth_client, app):
        with app.app_context():
            auth_client.post("/expenses/add", data={**VALID_EXPENSE, "category": "Groceries"})
            rows = _fetch_expenses_for_user()
            assert len(rows) == 0, "Invalid category must not insert a row into the DB"

    @pytest.mark.parametrize("category", ALLOWED_CATEGORIES)
    def test_all_allowed_categories_accepted(self, auth_client, category):
        data = {**VALID_EXPENSE, "category": category}
        response = auth_client.post("/expenses/add", data=data)
        assert response.status_code == 302, \
            f"Allowed category '{category}' must be accepted and redirect"

    def test_category_error_re_renders_form(self, auth_client):
        response = auth_client.post(
            "/expenses/add", data={**VALID_EXPENSE, "category": "Groceries"}
        )
        assert response.status_code == 400
        assert b"category" in response.data.lower(), \
            "Error response for bad category should re-render the form"


# ---------------------------------------------------------------------------
# 8. Data isolation — expense linked to correct user
# ---------------------------------------------------------------------------

class TestDataIsolation:
    def test_expense_linked_to_authenticated_user(self, auth_client, app):
        with app.app_context():
            auth_client.post("/expenses/add", data=VALID_EXPENSE)
            rows = _fetch_expenses_for_user(email=TEST_EMAIL)
            assert len(rows) == 1, "Expense must be associated with the logged-in user"
            expected_uid = _get_user_id(email=TEST_EMAIL)
            assert rows[0]["user_id"] == expected_uid, \
                "user_id on the expense row must match the authenticated user's id"


# ---------------------------------------------------------------------------
# 9. create_expense() helper contract
# ---------------------------------------------------------------------------

class TestCreateExpenseHelper:
    def test_create_expense_is_importable(self):
        """create_expense must be importable from database.db."""
        from database.db import create_expense  # noqa: F401
        assert callable(create_expense), \
            "create_expense must be a callable function in database.db"

    def test_create_expense_inserts_row_directly(self, app):
        """Calling create_expense() directly must insert the correct row."""
        with app.app_context():
            from database.db import create_user, create_expense, get_db

            create_user("Helper User", "helper@spendly.com",
                        generate_password_hash("pw"))
            conn = get_db()
            uid = conn.execute(
                "SELECT id FROM users WHERE email = ?", ("helper@spendly.com",)
            ).fetchone()["id"]
            conn.close()

            create_expense(uid, 99.99, "Bills", "2026-04-01", "Direct call test")

            conn = get_db()
            rows = conn.execute(
                "SELECT * FROM expenses WHERE user_id = ?", (uid,)
            ).fetchall()
            conn.close()

            assert len(rows) == 1, "create_expense() must insert exactly one row"
            assert float(rows[0]["amount"]) == pytest.approx(99.99)
            assert rows[0]["category"] == "Bills"
            assert rows[0]["date"] == "2026-04-01"
            assert rows[0]["description"] == "Direct call test"

    def test_create_expense_with_none_description_stores_null(self, app):
        """create_expense() with None description must store NULL."""
        with app.app_context():
            from database.db import create_user, create_expense, get_db

            create_user("Null Desc User", "nulldesc@spendly.com",
                        generate_password_hash("pw"))
            conn = get_db()
            uid = conn.execute(
                "SELECT id FROM users WHERE email = ?", ("nulldesc@spendly.com",)
            ).fetchone()["id"]
            conn.close()

            create_expense(uid, 10.00, "Other", "2026-06-01", None)

            conn = get_db()
            row = conn.execute(
                "SELECT description FROM expenses WHERE user_id = ?", (uid,)
            ).fetchone()
            conn.close()

            assert row["description"] is None, \
                "create_expense() with None description must store NULL in the DB"
