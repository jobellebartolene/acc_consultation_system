from flask import Blueprint, redirect, url_for
from flask_login import login_required, current_user

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    if not current_user.is_authenticated:
        return redirect(url_for("auth.login"))
    return redirect(url_for("main.dashboard"))


@main_bp.route("/dashboard")
@login_required
def dashboard():
    if current_user.is_super_admin:
        return redirect(url_for("admin.dashboard"))
    if current_user.is_medical_expert:
        return redirect(url_for("expert.dashboard"))
    return redirect(url_for("student.dashboard"))
