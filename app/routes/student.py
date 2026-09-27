from flask import Blueprint, render_template, abort
from flask_login import login_required, current_user

from app.models import Role, Consultation
from app.decorators import roles_required

student_bp = Blueprint("student", __name__)


@student_bp.before_request
@login_required
@roles_required(Role.STUDENT.value)
def guard():
    pass


@student_bp.route("/")
def dashboard():
    consultations = current_user.observed_consultations
    return render_template("student/dashboard.html", consultations=consultations)


@student_bp.route("/consultations/<int:cid>")
def consultation_detail(cid):
    consultation = next((c for c in current_user.observed_consultations if c.id == cid), None)
    if consultation is None:
        abort(403)
    return render_template("student/consultation_detail.html", consultation=consultation)
