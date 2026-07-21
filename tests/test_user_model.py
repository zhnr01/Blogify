"""User model and permission tests."""
from app.models import AnonymousUser, Permission, Role, User


def test_password_setter(app):
    u = User(password='cat')
    assert u.passwd_hash is not None


def test_no_password_getter(app):
    u = User(password='cat')
    try:
        u.password
    except AttributeError:
        return
    raise AssertionError('password should not be readable')


def test_password_verification(app):
    u = User(password='cat')
    assert u.verify_passwd('cat')
    assert not u.verify_passwd('dog')


def test_password_salts_are_random(app):
    u = User(password='cat')
    u2 = User(password='cat')
    assert u.passwd_hash != u2.passwd_hash


def test_default_role_permissions(app):
    Role.insert_roles()
    u = User(email='john@example.com', password='cat')
    assert u.can(Permission.WRITE)
    assert u.can(Permission.COMMENT)
    assert u.can(Permission.FOLLOW)
    assert not u.can(Permission.MODERATE_COMMENTS)
    assert not u.can(Permission.ADMINISTER)


def test_moderator_role(app):
    Role.insert_roles()
    role = Role.query.filter_by(name='Moderator').first()
    u = User(email='mod@example.com', password='cat', role=role)
    assert u.can(Permission.MODERATE_COMMENTS)
    assert not u.can(Permission.ADMINISTER)


def test_administrator_role(app):
    Role.insert_roles()
    role = Role.query.filter_by(name='Administrator').first()
    u = User(email='admin@example.com', password='cat', role=role)
    assert u.can(Permission.ADMINISTER)
    assert u.is_administrator()


def test_anonymous_user(app):
    u = AnonymousUser()
    assert not u.can(Permission.FOLLOW)
    assert not u.is_administrator()


def test_auth_token_roundtrip(app):
    Role.insert_roles()
    u = User(email='tok@example.com', password='cat')
    from app import db
    db.session.add(u)
    db.session.commit()
    token = u.generate_auth_token()
    assert User.verify_auth_token(token) == u


def test_invalid_auth_token_returns_none(app):
    assert User.verify_auth_token('not-a-real-token') is None
