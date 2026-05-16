"""Local development settings."""
from .base import *  # noqa: F401,F403

DEBUG = True
ALLOWED_HOSTS = ["*"]

# Always-fail-loudly during dev
SILENCED_SYSTEM_CHECKS: list[str] = []

# Console email backend in dev unless explicitly overridden
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Looser security so we can dev over http
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

INTERNAL_IPS = ["127.0.0.1"]
