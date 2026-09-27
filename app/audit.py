from flask import request
from flask_login import current_user

from app.extensions import db
from app.models import AuditLog


def log_action(action: str, details: str = None, username: str = None):
    """Record a sensitive action to the audit log. Never raises -- auditing
    failures must not break the request."""
    try:
        uid = current_user.id if getattr(current_user, "is_authenticated", False) else None
        uname = username or (current_user.username if getattr(current_user, "is_authenticated", False) else None)
        entry = AuditLog(
            user_id=uid,
            username=uname,
            action=action,
            details=details,
            ip_address=request.remote_addr if request else None,
        )
        db.session.add(entry)
        db.session.commit()
    except Exception:
        db.session.rollback()
