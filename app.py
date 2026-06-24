from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from database.db import (
    get_db, init_db, seed_db,
    create_user, get_user_by_email,
    get_expenses_for_user,
)
from database.queries import (
    get_user_by_id as get_user_profile,
    get_summary_stats,
    get_recent_transactions,
    get_category_breakdown,
)

app = Flask(__name__)
app.secret_key = "spendly-dev-secret"


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("profile"))

    if request.method == "GET":
        return render_template("register.html")

    name     = request.form.get("name", "").strip()
    email    = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    confirm  = request.form.get("confirm_password", "")

    if not name:
        return render_template("register.html", error="Name is required"), 400
    if not email:
        return render_template("register.html", error="Email is required"), 400
    if not password:
        return render_template("register.html", error="Password is required"), 400
    if password != confirm:
        return render_template("register.html", error="Passwords do not match"), 400
    if get_user_by_email(email):
        return render_template("register.html", error="Email already registered"), 400

    create_user(name, email, generate_password_hash(password))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("profile"))

    if request.method == "GET":
        return render_template("login.html")

    email    = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    if not email or not password:
        return render_template("login.html", error="Invalid email or password"), 400

    user = get_user_by_email(email)
    if not user or not check_password_hash(user["password_hash"], password):
        return render_template("login.html", error="Invalid email or password"), 400

    session.clear()
    session["user_id"] = user["id"]
    session["user_name"] = user["name"]
    return redirect(url_for("profile"))


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/terms", methods=["GET"])
def terms():
    return render_template("terms.html")


@app.route("/privacy", methods=["GET"])
def privacy():
    return render_template("privacy.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


@app.route("/profile")
def profile():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    user         = get_user_profile(user_id)
    summary      = get_summary_stats(user_id)
    transactions = get_recent_transactions(user_id, limit=10)
    breakdown    = get_category_breakdown(user_id)

    from datetime import datetime
    for tx in transactions:
        try:
            tx["date"] = datetime.strptime(tx["date"], "%Y-%m-%d").strftime("%B %d, %Y").replace(" 0", " ")
        except (ValueError, KeyError):
            pass

    return render_template(
        "profile.html",
        user         = user,
        summary      = summary,
        transactions = transactions,
        breakdown    = breakdown,
    )


@app.route("/expenses")
def expenses():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    from datetime import datetime
    rows = get_expenses_for_user(user_id)
    expenses_display = []
    for row in rows:
        try:
            date_fmt = datetime.strptime(row["date"], "%Y-%m-%d").strftime("%B %d, %Y").replace(" 0", " ")
        except ValueError:
            date_fmt = row["date"]
        expenses_display.append({
            "id":          row["id"],
            "date":        date_fmt,
            "category":    row["category"],
            "amount":      row["amount"],
            "description": row["description"] or "",
        })

    return render_template("expenses.html", expenses=expenses_display)


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    with app.app_context():
        init_db()
        seed_db()
    app.run(debug=True, port=5001)
