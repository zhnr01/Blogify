"""Comment API resources."""
from flask import current_app, g, jsonify, request, url_for
from marshmallow import ValidationError as SchemaValidationError

from app.models import Permission
from app.schemas import comment_schema, comments_schema
from app.services import comments as comment_service
from app.services import posts as post_service

from . import api
from .decorators import permission_required
from .errors import not_found, unprocessable
from .pagination import page_arg, paginate


@api.route('/comments/')
def get_comments():
    pagination = comment_service.list_all_comments(
        page=page_arg(),
        per_page=current_app.config['BLOGIFY_COMMENTS_PER_PAGE'],
    )
    return jsonify(paginate(
        pagination,
        comments_schema.dump(pagination.items),
        'api.get_comments',
    ))


@api.route('/comments/<int:id>')
def get_comment(id):
    comment = comment_service.get_comment(id)
    if comment is None:
        return not_found('comment not found')
    return jsonify(comment_schema.dump(comment))


@api.route('/posts/<int:id>/comments/')
def get_post_comments(id):
    post = post_service.get_post(id)
    if post is None:
        return not_found('post not found')
    pagination = comment_service.list_comments_for_post(
        post,
        page=page_arg(),
        per_page=current_app.config['BLOGIFY_COMMENTS_PER_PAGE'],
    )
    return jsonify(paginate(
        pagination,
        comments_schema.dump(pagination.items),
        'api.get_post_comments',
        id=id,
    ))


@api.route('/posts/<int:id>/comments/', methods=['POST'])
@permission_required(Permission.COMMENT)
def new_post_comment(id):
    post = post_service.get_post(id)
    if post is None:
        return not_found('post not found')
    try:
        data = comment_schema.load(request.get_json(silent=True) or {})
    except SchemaValidationError as err:
        return unprocessable(err.messages)

    comment = comment_service.create_comment(
        body=data['body'],
        post=post,
        author=g.current_user,
    )
    response = jsonify(comment_schema.dump(comment))
    response.status_code = 201
    response.headers['Location'] = url_for('api.get_comment', id=comment.id, _external=True)
    return response
