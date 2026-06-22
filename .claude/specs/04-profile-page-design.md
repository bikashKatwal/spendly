# Spec: Profile Page Design

## Overview
This step implements the `/profile` route, replacing the current stub string response with a real rendered page. The profile page is the authenticated home of the app — after login the user lands here and sees their account information (name, email, member since date) alongside a summary of their expense activity. It acts as the dashboard hub from which future steps (add, edit, delete expenses) will be linked.

## Depends on
- Step 01 — Database Setup (users and expenses tables exist)
- Step 02 — Registration (users can be created)
- Step 03 — Login and Logout (session established; `user_id` in session)

## Routes
- `GET /profile` — renders the profile page with user info and expense summary — logged-in only (redirect to `/login` if no session)

## Database changes
No new tables or columns required. The existing `users` and `expenses` tables are sufficient. A new DB helper `get_user_by_id` is needed to fetch the logged-in user's row, and a `get_expense_summary` helper to fetch aggregate stats.

## Templates
- **Create:** `templates/profile.html` — extends `base.html`; displays user name, email, member-since date, and expense summary stats (total expenses count, total amount spent, most recent expense date)
- **Modify:** `templates/base.html` — ensure the nav bar shows a "Profile" link and "Logout" link when a session exists, and hides them when not logged in (may already be partially done; verify and complete if needed)

## Files to change
- `app.py` — replace stub `profile()` route with a real implementation that checks session, fetches user + summary, and renders `profile.html`
- `database/db.py` — add `get_user_by_id(user_id)` and `get_expense_summary(user_id)` helpers
- `templates/base.html` — conditional nav links for logged-in vs logged-out state
- `static/css/style.css` — add profile card styles using existing CSS variables

## Files to create
- `templates/profile.html` — profile page template

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` only
- Parameterised queries only — `?` placeholders, never f-strings in SQL
- Passwords hashed with werkzeug (no password changes on this page; just display)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Route must call `abort(401)` or redirect to `/login` if `session.get("user_id")` is falsy — no unauthenticated access
- DB helpers belong in `database/db.py` only — no inline queries in `app.py`
- `get_expense_summary` must return a dict with at least: `count`, `total`, `latest_date`

## Definition of done
- [ ] Visiting `/profile` while logged out redirects to `/login`
- [ ] After login, `/profile` renders without error
- [ ] Profile page displays the logged-in user's name and email
- [ ] Profile page displays the member-since date (formatted, not raw ISO string)
- [ ] Profile page displays total number of expenses for that user
- [ ] Profile page displays total amount spent (formatted as currency)
- [ ] Profile page displays the date of the most recent expense (or a friendly "No expenses yet" message)
- [ ] Nav bar shows "Profile" and "Logout" links only when logged in
- [ ] Nav bar hides auth-only links when logged out
- [ ] Logging out from the profile page redirects to the landing page
- [ ] Page is styled using only CSS variables — no hardcoded hex values
- [ ] All internal links use `url_for()`
