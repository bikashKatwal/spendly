# Spec: Add Expense

## Overview
This feature implements the "Add Expense" form, allowing a logged-in user to record a new expense by submitting a category, amount, date, and optional description. It replaces the stub route at `GET /expenses/add` with a fully functional `GET`/`POST` route, adds a `create_expense()` DB helper, and renders a new `add_expense.html` template. This is the first write path for expense data in Spendly.

## Depends on
- Step 01 — Database Setup (expenses table exists in `init_db()`)
- Step 03 — Login/Logout (session-based auth)
- Step 06 — Date filter (expenses list page exists at `/expenses`)

## Routes
- `GET /expenses/add` — Render the add-expense form — logged-in only
- `POST /expenses/add` — Validate and insert a new expense row, then redirect to `/expenses` — logged-in only

## Database changes
No new tables or columns. The existing `expenses` table already has all required columns:
- `user_id`, `amount`, `category`, `date`, `description`, `created_at`

A new DB helper `create_expense()` must be added to `database/db.py`.

## Templates
- **Create:** `templates/add_expense.html` — Form with fields: category (select), amount (number), date (date input), description (textarea, optional). Must extend `base.html`.
- **Modify:** None required. The expenses list (`expenses.html`) already links to `/expenses/add` if such a link exists; no mandatory change.

## Files to change
- `app.py` — Replace the `add_expense()` stub with a full `GET`/`POST` implementation
- `database/db.py` — Add `create_expense(user_id, amount, category, date, description)` helper

## Files to create
- `templates/add_expense.html` — The add-expense form template

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` only
- Parameterised queries only — never f-strings in SQL
- Passwords are not involved here; no hashing needed
- Use CSS variables — never hardcode hex values in templates or stylesheets
- All templates extend `base.html`
- Redirect to `/expenses` on successful POST (use `url_for("expenses")`)
- Use `abort(401)` if the user is not logged in (no `user_id` in session)
- `amount` must be a positive number — reject zero and negative values
- `category` must be one of the allowed values: Food, Transport, Bills, Health, Entertainment, Shopping, Other
- `date` must match `YYYY-MM-DD` format — validate with the existing `_DATE_RE` regex already in `app.py`
- `description` is optional — store `None` if blank
- `create_expense()` must live in `database/db.py`, not inline in the route

## Definition of done
- [ ] `GET /expenses/add` renders a form with category select, amount input, date input, and description textarea
- [ ] Submitting the form with valid data inserts a row into `expenses` and redirects to `/expenses`
- [ ] The new expense appears in the expenses list after redirect
- [ ] Submitting with a missing or invalid amount shows an error on the form (does not redirect)
- [ ] Submitting with a missing or invalid date shows an error on the form (does not redirect)
- [ ] Submitting with an invalid category shows an error on the form (does not redirect)
- [ ] Visiting `GET /expenses/add` while logged out redirects to `/login`
- [ ] `create_expense()` is defined in `database/db.py` and uses a parameterised query
