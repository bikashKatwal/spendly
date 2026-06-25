# Spec: Date Filter for Profile Page

## Overview
Step 6 adds a date range filter to the expenses list page (`/expenses`) so users
can narrow their expense history to a specific period. A simple "From" and "To"
date input is rendered above the expenses table. Submitting the form reloads the
page with `date_from` and `date_to` as query parameters; the route passes them
to the DB helper, which applies them as SQL `WHERE` clauses. This is a pure
server-side filter — no JavaScript required. The profile page summary stats and
recent transactions are not affected by this filter.

## Depends on
- Step 1: Database setup (`expenses` table exists with a `date` column)
- Step 2: Registration (users exist in the database)
- Step 3: Login / Logout (`session["user_id"]` is set on login)
- Step 5: Backend connection (`get_expenses_for_user` exists in `database/db.py`)

## Routes
- `GET /expenses` — modified to accept optional `date_from` and `date_to` query
  parameters (YYYY-MM-DD strings) and pass them to `get_expenses_for_user` —
  logged-in only

## Database changes
No database changes. The `expenses.date` column (TEXT, stored as `YYYY-MM-DD`)
already supports range comparisons with `>=` and `<=`.

## Templates
- **Modify:** `templates/expenses.html`
  - Add a filter form above the table with two `<input type="date">` fields
    (`date_from`, `date_to`) and a Submit button
  - Pre-populate inputs with the current filter values if set
  - Add a "Clear" link that navigates to `/expenses` with no query params when
    a filter is active
  - Show a notice (e.g. "Showing filtered results") when a filter is active

## Files to change
- `database/db.py` — update `get_expenses_for_user(user_id)` to accept optional
  `date_from=None` and `date_to=None` keyword arguments and append them as
  parameterised `AND date >= ?` / `AND date <= ?` clauses when provided
- `app.py` — read `request.args.get("date_from")` and `request.args.get("date_to")`
  in the `expenses()` view and pass them to `get_expenses_for_user`; also pass
  the raw filter values back to the template for pre-populating the form
- `templates/expenses.html` — add the filter form (see Templates above)
- `static/css/style.css` — add styles for `.filter-form` and `.filter-notice`
  using existing CSS variables only

## Files to create
No new files.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` only via `get_db()`
- Parameterised queries only — never f-strings or string concatenation in SQL
- Date values from `request.args` must be validated: only accept strings matching
  `YYYY-MM-DD` (10 chars, digits and hyphens); ignore malformed values silently
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- No inline `<style>` tags — new styles go in `static/css/style.css`
- No JavaScript — the filter form must use `method="get"` and a standard submit
- The filter must not affect the profile page stats or recent transactions

## Definition of done
- [ ] Visiting `/expenses` with no query params shows all expenses (unchanged behaviour)
- [ ] Submitting the filter form with a valid date range shows only expenses within that range
- [ ] Submitting with only `date_from` set filters to expenses on or after that date
- [ ] Submitting with only `date_to` set filters to expenses on or before that date
- [ ] The filter inputs are pre-populated with the current filter values after submission
- [ ] A "Clear" link is visible when a filter is active and navigates back to `/expenses` with no params
- [ ] Entering no dates and submitting returns all expenses (same as no filter)
- [ ] A malformed date value in the query string does not cause a 500 error — it is silently ignored
- [ ] The empty-state message still appears correctly when the filter matches no expenses
