"""Security hardening: rate limiting, security headers, and CSRF.

The API uses token/basic auth and is exempt from session-cookie CSRF; HTML forms
are protected by Flask-WTF's CSRF token. Security response headers are applied to
every response.
"""
from flask import request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf import CSRFProtect

csrf = CSRFProtect()

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],  # opt-in per-route; a global default is set from config
    storage_uri="memory://",
)

# Response headers applied to every response. Kept conservative so the existing
# Bootstrap/PageDown/Gravatar assets keep working.
_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "SAMEORIGIN",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "X-XSS-Protection": "0",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
}


def init_security(app):
    """Bind CSRF, the rate limiter, and security-header handling to the app."""
    csrf.init_app(app)

    # The API authenticates per-request (token/basic auth), so exempt it from
    # the session-based CSRF that protects browser form posts.
    from .api import api as api_blueprint
    csrf.exempt(api_blueprint)

    # Flask-Limiter reads RATELIMIT_* keys (default, storage URI, enabled) from
    # app.config during init_app, so configuration stays in config.py.
    limiter.init_app(app)

    @app.after_request
    def apply_security_headers(response):
        for header, value in _SECURITY_HEADERS.items():
            response.headers.setdefault(header, value)
        # Only advertise HSTS over HTTPS to avoid breaking local http dev.
        if request.is_secure:
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )
        return response
