from flask import Blueprint, render_template, redirect, url_for, request, flash, abort
from flask_login import login_required, current_user

from app.extensions import db
from app.models import Role, Consultation, ClinicalNote, ConsultationStatus, User
from app.decorators import roles_required
from app.audit import log_action

expert_bp = Blueprint("expert", __name__)


@expert_bp.before_request
@login_required
@roles_required(Role.MEDICAL_EXPERT.value)
def guard():
    pass


def _get_owned_consultation_or_403(cid):
    consultation = db.session.get(Consultation, cid) or abort(404)
    if consultation.expert_id != current_user.id:
        abort(403)
    return consultation


@expert_bp.route("/")
def dashboard():
    consultations = (
        Consultation.query.filter_by(expert_id=current_user.id)
        .order_by(Consultation.updated_at.desc())
        .all()
    )
    stats = {
        "total": len(consultations),
        "open": sum(1 for c in consultations if c.status == ConsultationStatus.OPEN.value),
        "in_progress": sum(1 for c in consultations if c.status == ConsultationStatus.IN_PROGRESS.value),
        "closed": sum(1 for c in consultations if c.status == ConsultationStatus.CLOSED.value),
    }
    return render_template("expert/dashboard.html", consultations=consultations, stats=stats)


@expert_bp.route("/consultations/<int:cid>")
def consultation_detail(cid):
    consultation = _get_owned_consultation_or_403(cid)
    return render_template("expert/consultation_detail.html", consultation=consultation, statuses=ConsultationStatus.choices())


@expert_bp.route("/consultations/<int:cid>/update", methods=["POST"])
def consultation_update(cid):
    consultation = _get_owned_consultation_or_403(cid)

    diagnosis = (request.form.get("diagnosis") or "").strip()
    status = request.form.get("status")
    description = (request.form.get("description") or "").strip()

    if status not in [s.value for s in ConsultationStatus]:
        flash("Invalid status.", "error")
        return redirect(url_for("expert.consultation_detail", cid=cid))

    consultation.diagnosis = diagnosis
    consultation.status = status
    consultation.description = description
    db.session.commit()
    log_action("consultation_diagnosis_updated", f"Updated diagnosis/status for consultation #{cid}")
    flash("Patient record updated.", "success")
    return redirect(url_for("expert.consultation_detail", cid=cid))


@expert_bp.route("/consultations/<int:cid>/notes", methods=["POST"])
def add_note(cid):
    consultation = _get_owned_consultation_or_403(cid)

    content = (request.form.get("content") or "").strip()
    note_type = request.form.get("note_type", "note")

    if not content:
        flash("Note content cannot be empty.", "error")
        return redirect(url_for("expert.consultation_detail", cid=cid))

    if note_type not in ("note", "diagnosis"):
        note_type = "note"

    note = ClinicalNote(consultation_id=cid, author_id=current_user.id, content=content, note_type=note_type)
    db.session.add(note)
    db.session.commit()
    log_action("clinical_note_added", f"Added {note_type} to consultation #{cid}")
    flash("Note added.", "success")
    return redirect(url_for("expert.consultation_detail", cid=cid))
