from functools import wraps

from flask import abort
from flask_login import current_user


def roles_required(*roles):
    """Restrict a view to one or more roles. Returns 403 for authenticated
    users of the wrong role, and lets Flask-Login's @login_required (applied
    separately) handle anonymous users with a redirect to login."""

    def decorator(view_func):
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(403)
            if current_user.role not in roles:
                abort(403)
            if not current_user.is_active_account:
                abort(403)
            return view_func(*args, **kwargs)

        return wrapped

    return decorator
