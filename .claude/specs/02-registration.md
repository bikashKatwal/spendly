# Spec: Registration

## Overview
Step 2 implements user registration, allowing new users to create an account by providing their name, email, and password. The feature includes form validation on the backend, password hashing with werkzeug, and database persistence. Users who successfully register are redirected to the login page with a success message. Duplicate emails are rejected with a user-friendly error.

## Depends on
Step 1 — Database Setup (`database/db.py` with `get_db()`, `init_db()`, `seed_db()` and the users table schema)

## Routes
- `POST /register` — accepts form data (name, email, password, confirm_password); validates input; hashes password; inserts new user or returns error — public access

## Database changes
No new tables or schema changes. Uses the existing `users` table (id, name, email, password_hash, created_at).

## Templates
- **Create:** `register.html` — registration form with fields: name, email, password, confirm_password; displays error messages; extends `base.html`
- **Modify:** None

## Files to change
- `app.py` — add `POST /register` route handler with form validation and error handling
- `database/db.py` — add `create_user(name, email, password)` helper function

## Files to create
- `templates/register.html` — registration form template
- `static/css/register.css` — page-specific styles (optional; can use global styles only)

## New dependencies
No new dependencies. Uses existing werkzeug from Flask.

## Rules for implementation
- No SQLAlchemy or ORMs — use raw sqlite3 only
- Parameterised queries only — never f-strings in SQL
- Passwords hashed with `werkzeug.security.generate_password_hash()`
- Validate on backend: name not empty, email format valid, email unique, password non-empty, password matches confirm_password
- Use `abort(400)` for validation errors, not bare strings
- All templates extend `base.html`
- Use CSS variables — never hardcode hex values
- FK enforcement: call `PRAGMA foreign_keys = ON` in `get_db()`
- Port 5001 is the Flask dev server port (do not change)
- Only use Jinja2 templating in HTML — no vanilla JS form handling needed for basic version

## Definition of done
- [ ] `register.html` renders with form fields for name, email, password, confirm_password
- [ ] Form submission with valid data creates a user in the database
- [ ] Duplicate email returns a 400 error with message "Email already registered"
- [ ] Empty name/email/password returns a 400 error with appropriate message
- [ ] Password confirmation mismatch returns a 400 error with message "Passwords do not match"
- [ ] Successful registration redirects to `/login` with success message (use flash or template context)
- [ ] Password is stored hashed, not in plaintext
- [ ] No new pip packages added
