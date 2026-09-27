from datetime import datetime, timedelta

from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user

from app.extensions import db
from app.models import User
from app.audit import log_action

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""

        user = User.query.filter_by(username=username).first()

        # Generic error message on purpose -- avoid leaking which part was wrong
        generic_error = "Invalid username or password."

        if user is None:
            flash(generic_error, "error")
            return render_template("auth/login.html"), 401

        if user.is_locked():
            minutes_left = max(1, int((user.locked_until - datetime.utcnow()).total_seconds() // 60) + 1)
            flash(f"Account temporarily locked. Try again in {minutes_left} minute(s).", "error")
            return render_template("auth/login.html"), 401

        if not user.is_active_account:
            flash("This account has been disabled. Contact your administrator.", "error")
            return render_template("auth/login.html"), 403

        if not user.check_password(password):
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= current_app.config["MAX_LOGIN_ATTEMPTS"]:
                user.locked_until = datetime.utcnow() + timedelta(minutes=current_app.config["LOCKOUT_MINUTES"])
                user.failed_login_attempts = 0
                db.session.commit()
                log_action("login_lockout", f"Account locked after repeated failures", username=username)
                flash("Too many failed attempts. Account locked temporarily.", "error")
                return render_template("auth/login.html"), 401
            db.session.commit()
            flash(generic_error, "error")
            return render_template("auth/login.html"), 401

        # Success
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_at = datetime.utcnow()
        db.session.commit()

        login_user(user)
        log_action("login_success")
        flash(f"Welcome back, {user.full_name}.", "success")
        return redirect(url_for("main.dashboard"))

    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    log_action("logout")
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
