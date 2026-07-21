"""Consistent JSON error envelopes for the API.

Every error response has the same shape::

    {"error": "<slug>", "message": "<human readable>", ...}

so clients can branch on a stable ``error`` field.
"""
from flask import jsonify

from app.exceptions import ValidationError

from . import api


def _error(status, slug, message, **extra):
    payload = {'error': slug, 'message': message}
    payload.update(extra)
    response = jsonify(payload)
    response.status_code = status
    return response


def bad_request(message):
    return _error(400, 'bad_request', message)


def unauthorized(message):
    return _error(401, 'unauthorized', message)


def forbidden(message):
    return _error(403, 'forbidden', message)


def not_found(message='resource not found'):
    return _error(404, 'not_found', message)


def unprocessable(errors):
    """422 for schema validation failures; ``errors`` is a field->messages map."""
    return _error(422, 'validation_error', 'input failed validation', details=errors)


@api.errorhandler(ValidationError)
def validation_error(e):
    return bad_request(e.args[0] if e.args else 'invalid input')


@api.errorhandler(404)
def api_not_found(e):
    return not_found()
