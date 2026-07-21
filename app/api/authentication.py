"""HTTP Basic auth for the API.

Clients authenticate either with email + password, or by passing an auth token
as the username with an empty password. A successful auth stashes the resolved
user on ``flask.g`` for downstream handlers.
"""
from flask import g, jsonify
from flask_httpauth import HTTPBasicAuth

from app.models import User

from . import api
from .errors import forbidden, unauthorized

auth = HTTPBasicAuth()


@auth.verify_password
def verify_password(email_or_token, password):
    """Resolve credentials to a user, supporting token-as-username auth."""
    if email_or_token == '':
        return False
    if password == '':
        # Token-based auth: the token is supplied as the username.
        g.current_user = User.verify_auth_token(email_or_token)
        g.token_used = True
        return g.current_user is not None
    user = User.query.filter_by(email=email_or_token).first()
    if not user:
        return False
    g.current_user = user
    g.token_used = False
    return user.verify_passwd(password)


@auth.error_handler
def auth_error():
    return unauthorized('Invalid credentials')


@api.before_request
@auth.login_required
def before_request():
    """Require an authenticated, confirmed account for every API route."""
    if not g.current_user.is_anonymous and not g.current_user.confirmed:
        return forbidden('Unconfirmed account')


@api.route('/tokens/', methods=['POST'])
def get_token():
    """Issue a fresh auth token. Must authenticate with email + password."""
    if g.current_user.is_anonymous or g.token_used:
        return unauthorized('Invalid credentials')
    expiration = 3600
    return jsonify({
        'token': g.current_user.generate_auth_token(expiration=expiration),
        'expiration': expiration,
    })
