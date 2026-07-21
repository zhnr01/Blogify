"""Shared pytest fixtures.

Each test gets a fresh in-memory database inside an application context, plus
helpers for creating users and authenticating against the API.
"""
import base64

import pytest

from app import create_app, db as _db
from app.models import Role, User


@pytest.fixture
def app():
    app = create_app('testing')
    # A SERVER_NAME lets url_for(_external=True) work in serialization/tests.
    app.config['SERVER_NAME'] = 'localhost'
    with app.app_context():
        _db.create_all()
        Role.insert_roles()
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def db(app):
    return _db


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def make_user(db):
    """Factory to create a confirmed user with a known password."""
    def _make(email='user@example.com', username='user', password='password',
              confirmed=True, role_name=None):
        role = Role.query.filter_by(name=role_name).first() if role_name else None
        user = User(email=email, username=username, password=password,
                    confirmed=confirmed)
        if role is not None:
            user.role = role
        db.session.add(user)
        db.session.commit()
        return user
    return _make


@pytest.fixture
def user(make_user):
    return make_user()


def api_headers(email, password):
    """Basic-auth headers for the API."""
    token = base64.b64encode(f'{email}:{password}'.encode()).decode()
    return {
        'Authorization': 'Basic ' + token,
        'Accept': 'application/json',
        'Content-Type': 'application/json',
    }


@pytest.fixture
def auth_headers():
    return api_headers
