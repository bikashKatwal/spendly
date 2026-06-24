from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from database.db import (
    get_db, init_db, seed_db,
    create_user, get_user_by_email,
    get_user_by_id, get_expense_summary,
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

    user    = get_user_by_id(user_id)
    summary = get_expense_summary(user_id)

    from datetime import datetime
    raw_date = user["created_at"]
    try:
        member_since = datetime.strptime(raw_date, "%Y-%m-%d %H:%M:%S").strftime("%B %d, %Y").replace(" 0", " ")
    except ValueError:
        member_since = raw_date

    latest = summary["latest_date"]
    if latest:
        try:
            latest_display = datetime.strptime(latest, "%Y-%m-%d").strftime("%B %d, %Y").replace(" 0", " ")
        except ValueError:
            latest_display = latest
    else:
        latest_display = None

    return render_template(
        "profile.html",
        user          = user,
        member_since  = member_since,
        expense_count = summary["count"],
        expense_total = summary["total"],
        latest_date   = latest_display,
    )


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
