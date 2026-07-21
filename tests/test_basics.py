"""App bootstrap, health, and security-header smoke tests."""
from flask import current_app


def test_app_exists(app):
    assert current_app is not None


def test_app_is_testing(app):
    assert current_app.config['TESTING']


def test_healthz(client):
    resp = client.get('/healthz')
    assert resp.status_code == 200
    assert resp.get_json()['status'] == 'ok'


def test_readyz(client):
    resp = client.get('/readyz')
    assert resp.status_code == 200
    assert resp.get_json()['status'] == 'ready'


def test_request_id_header(client):
    resp = client.get('/healthz')
    assert resp.headers.get('X-Request-ID')


def test_security_headers(client):
    resp = client.get('/healthz')
    assert resp.headers.get('X-Content-Type-Options') == 'nosniff'
    assert resp.headers.get('X-Frame-Options') == 'SAMEORIGIN'
