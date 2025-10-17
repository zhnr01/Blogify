from flask import g, jsonify

from app.models import User
from flask_httpauth import HTTPBasicAuth


auth = HTTPBasicAuth()


'''
    This will be called when a decorator regitered with @auth.login_required is accessed be the client.
    It will be automatically called to verify password.
'''


@auth.verify_password
def verify_passwd(email_or_token, password):
    if email_or_token == '':
        return False
    if password == '':
        g.current_user = User.query.filter_by(email=email_or_token).first()
        g.token_used = True
        return g.current_user is not None
    user = User.query.filter_by(email=email_or_token).first()
    if not user:
        return False
    g.current_user = user
    g.token_used = False
    return user.verify_passwd(password)


'''
    Since all the routes need a login so we can register the before_request function to check for logins
'''
from .errors import forbidden, unauthorized
from . import api
@api.before_request
@auth.login_required
def before_request():
    if not g.current_user.is_anonymous and \
            not g.current_user.confirmed:
        return forbidden('Unconfirmed account')


@api.route('/tokens/', methods=['POST'])
def get_token():
    if g.current_user.is_anonymous or g.token_used:
        return unauthorized('Invalid credentials')
    return jsonify({'token': g.current_user.generate_auth_token(
        expiration=3600), 'expiration': 3600})


@auth.error_handler
def auth_error():
    return unauthorized('Invalid credentials')




