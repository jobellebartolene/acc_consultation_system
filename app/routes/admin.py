from flask import Blueprint, render_template, redirect, url_for, request, flash, abort
from flask_login import login_required, current_user

from app.extensions import db
from app.models import User, Role, Consultation, ConsultationStatus, ClinicalNote
from app.decorators import roles_required
from app.audit import log_action

admin_bp = Blueprint("admin", __name__)


@admin_bp.before_request
@login_required
@roles_required(Role.SUPER_ADMIN.value)
def guard():
    """Applies login_required + role check to every route in this blueprint."""
    pass


@admin_bp.route("/")
def dashboard():
    stats = {
        "total_users": User.query.count(),
        "total_experts": User.query.filter_by(role=Role.MEDICAL_EXPERT.value).count(),
        "total_students": User.query.filter_by(role=Role.STUDENT.value).count(),
        "total_consultations": Consultation.query.count(),
        "open_consultations": Consultation.query.filter_by(status=ConsultationStatus.OPEN.value).count(),
    }
    recent_consultations = Consultation.query.order_by(Consultation.created_at.desc()).limit(5).all()
    return render_template("admin/dashboard.html", stats=stats, recent_consultations=recent_consultations)


# ------------------------------------------------------------------ Users --

@admin_bp.route("/users")
def user_list():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin/users.html", users=users, roles=Role.choices())


@admin_bp.route("/users/create", methods=["GET", "POST"])
def user_create():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        full_name = (request.form.get("full_name") or "").strip()
        role = request.form.get("role")
        password = request.form.get("password") or ""

        errors = []
        if not username or len(username) < 3:
            errors.append("Username must be at least 3 characters.")
        if not full_name:
            errors.append("Full name is required.")
        if not email or "@" not in email:
            errors.append("A valid email is required.")
        if role not in [r.value for r in Role]:
            errors.append("Invalid role selected.")
        if len(password) < 8:
            errors.append("Password must be at least 8 characters.")
        if User.query.filter_by(username=username).first():
            errors.append("That username is already taken.")
        if User.query.filter_by(email=email).first():
            errors.append("That email is already registered.")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("admin/user_form.html", roles=Role.choices(), form=request.form), 400

        user = User(username=username, email=email, full_name=full_name, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        log_action("user_created", f"Created user '{username}' with role {role}")
        flash(f"User '{username}' created successfully.", "success")
        return redirect(url_for("admin.user_list"))

    return render_template("admin/user_form.html", roles=Role.choices(), form={})


@admin_bp.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
def user_edit(user_id):
    user = db.session.get(User, user_id) or abort(404)

    if request.method == "POST":
        full_name = (request.form.get("full_name") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        role = request.form.get("role")
        new_password = request.form.get("password") or ""

        errors = []
        if not full_name:
            errors.append("Full name is required.")
        if not email or "@" not in email:
            errors.append("A valid email is required.")
        if role not in [r.value for r in Role]:
            errors.append("Invalid role selected.")
        existing = User.query.filter(User.email == email, User.id != user.id).first()
        if existing:
            errors.append("That email is already registered to another user.")
        if new_password and len(new_password) < 8:
            errors.append("New password must be at least 8 characters.")

        if user.id == current_user.id and role != Role.SUPER_ADMIN.value:
            errors.append("You cannot remove your own Super Admin role.")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("admin/user_form.html", roles=Role.choices(), form=request.form, user=user), 400

        user.full_name = full_name
        user.email = email
        user.role = role
        if new_password:
            user.set_password(new_password)
        db.session.commit()
        log_action("user_updated", f"Updated user '{user.username}'")
        flash(f"User '{user.username}' updated.", "success")
        return redirect(url_for("admin.user_list"))

    return render_template("admin/user_form.html", roles=Role.choices(), user=user, form={})


@admin_bp.route("/users/<int:user_id>/toggle-active", methods=["POST"])
def user_toggle_active(user_id):
    user = db.session.get(User, user_id) or abort(404)
    if user.id == current_user.id:
        flash("You cannot disable your own account.", "error")
        return redirect(url_for("admin.user_list"))

    user.is_active_account = not user.is_active_account
    db.session.commit()
    state = "enabled" if user.is_active_account else "disabled"
    log_action("user_status_changed", f"User '{user.username}' {state}")
    flash(f"User '{user.username}' {state}.", "success")
    return redirect(url_for("admin.user_list"))


@admin_bp.route("/users/<int:user_id>/delete", methods=["POST"])
def user_delete(user_id):
    user = db.session.get(User, user_id) or abort(404)
    if user.id == current_user.id:
        flash("You cannot delete your own account.", "error")
        return redirect(url_for("admin.user_list"))

    username = user.username
    db.session.delete(user)
    db.session.commit()
    log_action("user_deleted", f"Deleted user '{username}'")
    flash(f"User '{username}' deleted.", "success")
    return redirect(url_for("admin.user_list"))


# ------------------------------------------------------------ Consultations --

@admin_bp.route("/consultations")
def consultation_list():
    consultations = Consultation.query.order_by(Consultation.created_at.desc()).all()
    return render_template("admin/consultations.html", consultations=consultations)


@admin_bp.route("/consultations/create", methods=["GET", "POST"])
def consultation_create():
    experts = User.query.filter_by(role=Role.MEDICAL_EXPERT.value, is_active_account=True).all()
    students = User.query.filter_by(role=Role.STUDENT.value, is_active_account=True).all()

    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        patient_name = (request.form.get("patient_name") or "").strip()
        patient_age = request.form.get("patient_age") or None
        patient_gender = request.form.get("patient_gender") or None
        description = (request.form.get("description") or "").strip()
        expert_id = request.form.get("expert_id") or None
        student_ids = request.form.getlist("student_ids")

        errors = []
        if not title:
            errors.append("Title is required.")
        if not patient_name:
            errors.append("Patient name is required.")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template(
                "admin/consultation_form.html", experts=experts, students=students, form=request.form
            ), 400

        consultation = Consultation(
            title=title,
            patient_name=patient_name,
            patient_age=int(patient_age) if patient_age else None,
            patient_gender=patient_gender,
            description=description,
            expert_id=int(expert_id) if expert_id else None,
            created_by_id=current_user.id,
        )
        if student_ids:
            consultation.observing_students = User.query.filter(User.id.in_(student_ids)).all()

        db.session.add(consultation)
        db.session.commit()
        log_action("consultation_created", f"Created consultation '{title}'")
        flash("Consultation created.", "success")
        return redirect(url_for("admin.consultation_list"))

    return render_template("admin/consultation_form.html", experts=experts, students=students, form={})


@admin_bp.route("/consultations/<int:cid>/edit", methods=["GET", "POST"])
def consultation_edit(cid):
    consultation = db.session.get(Consultation, cid) or abort(404)
    experts = User.query.filter_by(role=Role.MEDICAL_EXPERT.value, is_active_account=True).all()
    students = User.query.filter_by(role=Role.STUDENT.value, is_active_account=True).all()

    if request.method == "POST":
        consultation.title = (request.form.get("title") or "").strip()
        consultation.patient_name = (request.form.get("patient_name") or "").strip()
        patient_age = request.form.get("patient_age") or None
        consultation.patient_age = int(patient_age) if patient_age else None
        consultation.patient_gender = request.form.get("patient_gender") or None
        consultation.description = (request.form.get("description") or "").strip()
        consultation.status = request.form.get("status") or consultation.status
        expert_id = request.form.get("expert_id") or None
        consultation.expert_id = int(expert_id) if expert_id else None

        student_ids = request.form.getlist("student_ids")
        consultation.observing_students = User.query.filter(User.id.in_(student_ids)).all() if student_ids else []

        db.session.commit()
        log_action("consultation_updated", f"Updated consultation #{cid}")
        flash("Consultation updated.", "success")
        return redirect(url_for("admin.consultation_list"))

    return render_template(
        "admin/consultation_form.html",
        experts=experts,
        students=students,
        consultation=consultation,
        form={},
        status_choices=ConsultationStatus.choices(),
    )


@admin_bp.route("/consultations/<int:cid>/delete", methods=["POST"])
def consultation_delete(cid):
    consultation = db.session.get(Consultation, cid) or abort(404)
    title = consultation.title
    db.session.delete(consultation)
    db.session.commit()
    log_action("consultation_deleted", f"Deleted consultation '{title}'")
    flash("Consultation deleted.", "success")
    return redirect(url_for("admin.consultation_list"))


@admin_bp.route("/consultations/<int:cid>")
def consultation_detail(cid):
    consultation = db.session.get(Consultation, cid) or abort(404)
    return render_template("admin/consultation_detail.html", consultation=consultation)


# ----------------------------------------------------------------- Settings --

@admin_bp.route("/settings")
def settings():
    return render_template("admin/settings.html")
