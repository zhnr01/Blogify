"""Post API resources."""
from flask import current_app, g, jsonify, request, url_for
from marshmallow import ValidationError as SchemaValidationError

from app.models import Permission
from app.schemas import post_schema, posts_schema
from app.services import posts as post_service

from . import api
from .decorators import permission_required
from .errors import not_found, unprocessable
from .pagination import page_arg, paginate


@api.route('/posts/')
def get_posts():
    pagination = post_service.list_posts(
        page=page_arg(),
        per_page=current_app.config['BLOGIFY_POSTS_PER_PAGE'],
    )
    return jsonify(paginate(
        pagination,
        posts_schema.dump(pagination.items),
        'api.get_posts',
    ))


@api.route('/posts/<int:id>')
def get_post(id):
    post = post_service.get_post(id)
    if post is None:
        return not_found('post not found')
    return jsonify(post_schema.dump(post))


@api.route('/posts/', methods=['POST'])
@permission_required(Permission.WRITE)
def new_post():
    try:
        data = post_schema.load(request.get_json(silent=True) or {})
    except SchemaValidationError as err:
        return unprocessable(err.messages)

    post = post_service.create_post(
        title=data.get('title'),
        body=data['body'],
        author=g.current_user,
    )
    response = jsonify(post_schema.dump(post))
    response.status_code = 201
    response.headers['Location'] = url_for('api.get_post', id=post.id, _external=True)
    return response


@api.route('/posts/<int:id>', methods=['PUT'])
@permission_required(Permission.WRITE)
def edit_post(id):
    post = post_service.get_post(id)
    if post is None:
        return not_found('post not found')
    if g.current_user != post.author and not g.current_user.can(Permission.ADMINISTER):
        return not_found('post not found')
    try:
        data = post_schema.load(request.get_json(silent=True) or {})
    except SchemaValidationError as err:
        return unprocessable(err.messages)

    post = post_service.update_post(post, title=data.get('title'), body=data['body'])
    return jsonify(post_schema.dump(post))
