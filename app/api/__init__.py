"""Versioned REST API blueprint (mounted at /api/v1)."""
from flask import Blueprint

api = Blueprint('api', __name__)

# Import resource modules so their routes/handlers register on the blueprint.
from . import authentication, comments, errors, posts, users  # noqa: E402,F401
