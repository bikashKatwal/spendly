import sqlite3
import os
from database.db import get_db


def get_recent_transactions(user_id, limit=10):
    conn = get_db()
    rows = conn.execute(
        """
        SELECT date, description, category, amount
        FROM expenses
        WHERE user_id = ?
        ORDER BY date DESC, id DESC
        LIMIT ?
        """,
        (user_id, limit)
    ).fetchall()
    conn.close()
    return [
        {
            "date":        row["date"],
            "description": row["description"] or "",
            "category":    row["category"],
            "amount":      row["amount"],
        }
        for row in rows
    ]


def get_user_by_id(user_id):
    conn = get_db()
    row = conn.execute(
        "SELECT name, email, created_at FROM users WHERE id = ?",
        (user_id,)
    ).fetchone()
    conn.close()
    if row is None:
        return None
    from datetime import datetime
    raw = row["created_at"]
    try:
        member_since = datetime.strptime(raw, "%Y-%m-%d %H:%M:%S").strftime("%B %Y")
    except ValueError:
        member_since = raw
    return {
        "name":         row["name"],
        "email":        row["email"],
        "member_since": member_since,
    }


def get_summary_stats(user_id):
    conn = get_db()
    agg = conn.execute(
        """
        SELECT
            COALESCE(SUM(amount), 0.0) AS total_spent,
            COUNT(*)                   AS transaction_count
        FROM expenses
        WHERE user_id = ?
        """,
        (user_id,)
    ).fetchone()
    top = conn.execute(
        """
        SELECT category
        FROM expenses
        WHERE user_id = ?
        GROUP BY category
        ORDER BY SUM(amount) DESC
        LIMIT 1
        """,
        (user_id,)
    ).fetchone()
    conn.close()
    return {
        "total_spent":       agg["total_spent"],
        "transaction_count": agg["transaction_count"],
        "top_category":      top["category"] if top else "—",
    }


def get_category_breakdown(user_id):
    """Returns list of dicts ordered by amount desc: name, amount, pct (integers summing to 100)."""
    conn = get_db()
    rows = conn.execute(
        """
        SELECT category AS name, SUM(amount) AS amount
        FROM expenses
        WHERE user_id = ?
        GROUP BY category
        ORDER BY amount DESC
        """,
        (user_id,)
    ).fetchall()
    conn.close()
    if not rows:
        return []
    total = sum(row["amount"] for row in rows)
    result = []
    for row in rows:
        result.append({
            "name":   row["name"],
            "amount": row["amount"],
            "pct":    int(row["amount"] / total * 100),
        })
    # Adjust largest category so percentages sum exactly to 100
    diff = 100 - sum(item["pct"] for item in result)
    if result:
        result[0]["pct"] += diff
    return result
