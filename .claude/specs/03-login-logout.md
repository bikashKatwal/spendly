# Spec: Login and Logout

## Overview
Step 3 implements user authentication: the POST /login route validates email and password credentials, creates a session, and logs the user in; the GET /logout route clears the session and logs the user out. Users can only access protected routes (profile, expense tracking) when logged in. Session management uses Flask's built-in session object with a secret key. Login uses werkzeug's check_password_hash for secure password verification.

## Depends on
Step 2 — Registration (user creation, password hashing)

## Routes
- `POST /login` — accepts form data (email, password); validates credentials against database; creates session if valid; redirects to /profile or returns error — public access
- `GET /logout` — clears session; redirects to landing page — logged-in access (should work for logged-out users too, just redirects)

## Database changes
No new tables or schema changes. Uses the existing `users` table to query and verify credentials.

## Templates
- **Modify:** `login.html` — add POST form with email and password fields; display error messages on validation failure; extends `base.html`

## Files to change
- `app.py` — implement `POST /login` route handler with form validation and credential checking; implement `GET /logout` route handler; add session secret key configuration
- `database/db.py` — add `get_user_by_email_with_hash(email)` helper function to fetch user with password_hash for verification

## Files to create
None

## New dependencies
No new dependencies. Uses Flask's built-in `session` object.

## Rules for implementation
- No SQLAlchemy or ORMs — use raw sqlite3 only
- Parameterised queries only — never f-strings in SQL
- Passwords verified with `werkzeug.security.check_password_hash()`
- Set `app.secret_key` before using sessions (use a fixed string or environment variable)
- Validate on backend: email not empty, password not empty, credentials valid
- Use `abort()` for HTTP errors, not bare strings
- All templates extend `base.html`
- Use CSS variables — never hardcode hex values
- FK enforcement: call `PRAGMA foreign_keys = ON` in `get_db()`
- Session data stored in Flask session (encrypted in cookie)
- Redirect to `/` on logout, redirect to `/profile` on successful login
- Use `url_for()` in templates for all internal links

## Definition of done
- [ ] `login.html` renders with form fields for email and password
- [ ] Form submission with valid credentials logs user in and redirects to `/profile`
- [ ] Empty email/password returns a 400 error with appropriate message
- [ ] Non-existent email or wrong password returns a 400 error with message "Invalid email or password"
- [ ] User session is created after successful login (check `session['user_id']`)
- [ ] `/logout` route clears session and redirects to landing page
- [ ] Logged-out users see a login link in navbar; logged-in users see their name and logout link
- [ ] No new pip packages added
- [ ] All queries use parameterized SQL
- [ ] Password verification uses `check_password_hash()`, never plain-text comparison
