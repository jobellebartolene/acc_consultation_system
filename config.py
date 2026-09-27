import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Base configuration. Override sensitive values via environment variables in production."""

    # SECURITY: In production, SECRET_KEY MUST be set via environment variable.
    # A random fallback is generated per-process so the app never runs with a
    # hardcoded, predictable secret -- but this means sessions won't survive
    # a restart unless you set FLASK_SECRET_KEY yourself.
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY") or os.urandom(32).hex()

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'acc_consultation.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Session / cookie security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    # Set to True when serving over HTTPS in production
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "False") == "True"
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)

    # CSRF (Flask-WTF)
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None

    # Login lockout settings (simple in-memory-ish, DB-backed)
    MAX_LOGIN_ATTEMPTS = 5
    LOCKOUT_MINUTES = 15


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}
