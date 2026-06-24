import sqlite3
import os
from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "spendly.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_user_by_email(email):
    conn = get_db()
    row = conn.execute(
        "SELECT id, name, email, password_hash FROM users WHERE email = ?", (email,)
    ).fetchone()
    conn.close()
    return row


def get_user_by_id(user_id):
    conn = get_db()
    row = conn.execute(
        "SELECT id, name, email, created_at FROM users WHERE id = ?",
        (user_id,)
    ).fetchone()
    conn.close()
    return row


def get_expense_summary(user_id):
    conn = get_db()
    row = conn.execute(
        """
        SELECT
            COUNT(*)                   AS count,
            COALESCE(SUM(amount), 0.0) AS total,
            MAX(date)                  AS latest_date
        FROM expenses
        WHERE user_id = ?
        """,
        (user_id,)
    ).fetchone()
    conn.close()
    return {
        "count":       row["count"],
        "total":       row["total"],
        "latest_date": row["latest_date"],
    }


def get_expenses_for_user(user_id):
    conn = get_db()
    rows = conn.execute(
        """
        SELECT id, amount, category, date, description
        FROM expenses
        WHERE user_id = ?
        ORDER BY date DESC, id DESC
        """,
        (user_id,)
    ).fetchall()
    conn.close()
    return rows


def create_user(name, email, password_hash):
    conn = get_db()
    conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        (name, email, password_hash),
    )
    conn.commit()
    conn.close()


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT    NOT NULL,
            email         TEXT    UNIQUE NOT NULL,
            password_hash TEXT    NOT NULL,
            created_at    TEXT    DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES users(id),
            amount      REAL    NOT NULL,
            category    TEXT    NOT NULL,
            date        TEXT    NOT NULL,
            description TEXT,
            created_at  TEXT    DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    conn.close()


def seed_db():
    conn = get_db()
    row_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if row_count > 0:
        conn.close()
        return

    hashed_pw = generate_password_hash("demo123")
    cursor = conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Demo User", "demo@spendly.com", hashed_pw),
    )
    user_id = cursor.lastrowid

    expenses = [
        (user_id, 12.50,  "Food",          "2026-06-01", "Lunch at cafe"),
        (user_id, 35.00,  "Transport",     "2026-06-03", "Monthly bus pass top-up"),
        (user_id, 120.00, "Bills",         "2026-06-05", "Electricity bill"),
        (user_id, 45.00,  "Health",        "2026-06-08", "Pharmacy - vitamins"),
        (user_id, 18.00,  "Entertainment", "2026-06-10", "Streaming subscription"),
        (user_id, 65.00,  "Shopping",      "2026-06-12", "New running shoes"),
        (user_id, 9.90,   "Other",         "2026-06-15", "Parking meter"),
        (user_id, 22.00,  "Food",          "2026-06-18", "Grocery top-up"),
    ]
    conn.executemany(
        "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
        expenses,
    )
    conn.commit()
    conn.close()
