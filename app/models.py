from datetime import datetime
from enum import Enum

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db


class Role(str, Enum):
    SUPER_ADMIN = "super_admin"
    MEDICAL_EXPERT = "medical_expert"
    STUDENT = "student"

    @classmethod
    def choices(cls):
        return [(r.value, r.value.replace("_", " ").title()) for r in cls]


# Association table: which students are assigned to observe which consultations
consultation_observers = db.Table(
    "consultation_observers",
    db.Column("consultation_id", db.Integer, db.ForeignKey("consultations.id"), primary_key=True),
    db.Column("student_id", db.Integer, db.ForeignKey("users.id"), primary_key=True),
    db.Column("assigned_at", db.DateTime, default=datetime.utcnow),
)


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    full_name = db.Column(db.String(150), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(30), nullable=False, default=Role.STUDENT.value)
    is_active_account = db.Column(db.Boolean, default=True, nullable=False)

    failed_login_attempts = db.Column(db.Integer, default=0, nullable=False)
    locked_until = db.Column(db.DateTime, nullable=True)
    last_login_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Consultations this user owns/manages as the assigned Medical Expert
    owned_consultations = db.relationship(
        "Consultation", back_populates="expert", foreign_keys="Consultation.expert_id"
    )

    # Consultations this user (student) is assigned to observe
    observed_consultations = db.relationship(
        "Consultation",
        secondary=consultation_observers,
        back_populates="observing_students",
    )

    notes_authored = db.relationship("ClinicalNote", back_populates="author")

    # --- Password helpers -------------------------------------------------
    def set_password(self, raw_password: str) -> None:
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password_hash, raw_password)

    # Flask-Login requires get_id (UserMixin provides it via self.id) and
    # we override is_active to respect account disabling + lockout.
    @property
    def is_active(self):  # noqa: A003 - Flask-Login expects this name
        return self.is_active_account

    # --- Role helpers -------------------------------------------------
    @property
    def is_super_admin(self):
        return self.role == Role.SUPER_ADMIN.value

    @property
    def is_medical_expert(self):
        return self.role == Role.MEDICAL_EXPERT.value

    @property
    def is_student(self):
        return self.role == Role.STUDENT.value

    @property
    def role_label(self):
        return self.role.replace("_", " ").title()

    def is_locked(self):
        if self.locked_until is None:
            return False
        return datetime.utcnow() < self.locked_until

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"


class ConsultationStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"

    @classmethod
    def choices(cls):
        return [(s.value, s.value.replace("_", " ").title()) for s in cls]


class Consultation(db.Model):
    __tablename__ = "consultations"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)

    # Patient info (kept simple / de-identified for a demo system)
    patient_name = db.Column(db.String(150), nullable=False)
    patient_age = db.Column(db.Integer, nullable=True)
    patient_gender = db.Column(db.String(20), nullable=True)
    description = db.Column(db.Text, nullable=True)
    diagnosis = db.Column(db.Text, nullable=True)

    status = db.Column(db.String(20), default=ConsultationStatus.OPEN.value, nullable=False)

    expert_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    expert = db.relationship("User", back_populates="owned_consultations", foreign_keys=[expert_id])
    creator = db.relationship("User", foreign_keys=[created_by_id])

    observing_students = db.relationship(
        "User",
        secondary=consultation_observers,
        back_populates="observed_consultations",
    )

    notes = db.relationship(
        "ClinicalNote", back_populates="consultation", cascade="all, delete-orphan", order_by="ClinicalNote.created_at"
    )

    def __repr__(self):
        return f"<Consultation {self.id} - {self.title}>"


class ClinicalNote(db.Model):
    __tablename__ = "clinical_notes"

    id = db.Column(db.Integer, primary_key=True)
    consultation_id = db.Column(db.Integer, db.ForeignKey("consultations.id"), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    note_type = db.Column(db.String(30), default="note", nullable=False)  # note | diagnosis
    content = db.Column(db.Text, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    consultation = db.relationship("Consultation", back_populates="notes")
    author = db.relationship("User", back_populates="notes_authored")


class AuditLog(db.Model):
    """Lightweight audit trail for sensitive actions (login, user mgmt, consultation edits)."""

    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    username = db.Column(db.String(80), nullable=True)
    action = db.Column(db.String(120), nullable=False)
    details = db.Column(db.String(500), nullable=True)
    ip_address = db.Column(db.String(64), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
