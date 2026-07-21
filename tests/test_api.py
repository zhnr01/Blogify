"""Integration tests for the REST API, including auth and permissions."""


def test_anonymous_is_rejected(client):
    resp = client.get('/api/v1/posts/')
    assert resp.status_code == 401
    assert resp.get_json()['error'] == 'unauthorized'


def test_unconfirmed_account_is_forbidden(client, make_user, auth_headers):
    make_user(email='u@e.com', username='u', password='pw', confirmed=False)
    resp = client.get('/api/v1/posts/', headers=auth_headers('u@e.com', 'pw'))
    assert resp.status_code == 403
    assert resp.get_json()['error'] == 'forbidden'


def test_create_post(client, user, auth_headers):
    resp = client.post(
        '/api/v1/posts/',
        headers=auth_headers('user@example.com', 'password'),
        json={'title': 'Hi', 'body': 'hello world'},
    )
    assert resp.status_code == 201
    body = resp.get_json()
    assert body['title'] == 'Hi'
    assert body['body'] == 'hello world'
    assert resp.headers.get('Location')


def test_create_post_validation_error(client, user, auth_headers):
    resp = client.post(
        '/api/v1/posts/',
        headers=auth_headers('user@example.com', 'password'),
        json={'title': 'no body'},
    )
    assert resp.status_code == 422
    payload = resp.get_json()
    assert payload['error'] == 'validation_error'
    assert 'body' in payload['details']


def test_get_missing_post_returns_envelope(client, user, auth_headers):
    resp = client.get('/api/v1/posts/9999', headers=auth_headers('user@example.com', 'password'))
    assert resp.status_code == 404
    assert resp.get_json()['error'] == 'not_found'


def test_pagination_envelope(client, user, auth_headers):
    headers = auth_headers('user@example.com', 'password')
    for i in range(3):
        client.post('/api/v1/posts/', headers=headers,
                    json={'title': f't{i}', 'body': f'body number {i}'})
    resp = client.get('/api/v1/posts/', headers=headers)
    data = resp.get_json()
    assert 'items' in data and 'meta' in data
    assert data['meta']['total'] == 3


def test_token_auth_flow(client, user, auth_headers):
    # Exchange credentials for a token, then use it as the basic-auth username.
    resp = client.post('/api/v1/tokens/', headers=auth_headers('user@example.com', 'password'))
    assert resp.status_code == 200
    token = resp.get_json()['token']

    import base64
    tok_header = {
        'Authorization': 'Basic ' + base64.b64encode(f'{token}:'.encode()).decode(),
        'Accept': 'application/json',
    }
    resp = client.get('/api/v1/posts/', headers=tok_header)
    assert resp.status_code == 200


def test_token_cannot_be_used_to_get_token(client, user, auth_headers):
    resp = client.post('/api/v1/tokens/', headers=auth_headers('user@example.com', 'password'))
    token = resp.get_json()['token']
    import base64
    tok_header = {
        'Authorization': 'Basic ' + base64.b64encode(f'{token}:'.encode()).decode(),
    }
    resp = client.post('/api/v1/tokens/', headers=tok_header)
    assert resp.status_code == 401


def test_comment_permission_enforced(client, make_user, auth_headers):
    # A user whose role lacks COMMENT cannot post comments.
    author = make_user(email='a@e.com', username='author', password='pw')
    # Create a post to comment on.
    resp = client.post('/api/v1/posts/', headers=auth_headers('a@e.com', 'pw'),
                       json={'title': 'p', 'body': 'a post body'})
    post_id = resp.get_json()['id']

    # Strip the commenter's permissions by giving them an empty role.
    from app import db
    from app.models import Role
    empty = Role(name='NoPerms', permissions=0, default=False)
    db.session.add(empty)
    db.session.commit()
    commenter = make_user(email='c@e.com', username='commenter', password='pw')
    commenter.role = empty
    db.session.add(commenter)
    db.session.commit()

    resp = client.post(
        f'/api/v1/posts/{post_id}/comments/',
        headers=auth_headers('c@e.com', 'pw'),
        json={'body': 'blocked comment'},
    )
    assert resp.status_code == 403
