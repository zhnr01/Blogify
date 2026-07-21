"""User API resources (read-only public profiles and their posts)."""
from flask import current_app, jsonify

from app import db
from app.models import Post, User
from app.schemas import posts_schema, user_schema


from . import api
from .errors import not_found
from .pagination import page_arg, paginate


@api.route('/users/<int:id>')
def get_user(id):
    user = db.session.get(User, id)
    if user is None:
        return not_found('user not found')
    return jsonify(user_schema.dump(user))


@api.route('/users/<int:id>/posts/')
def get_user_posts(id):
    user = db.session.get(User, id)
    if user is None:
        return not_found('user not found')
    pagination = user.posts.order_by(Post.timestamp.desc()).paginate(
        page=page_arg(),
        per_page=current_app.config['BLOGIFY_POSTS_PER_PAGE'],
        error_out=False,
    )
    return jsonify(paginate(
        pagination,
        posts_schema.dump(pagination.items),
        'api.get_user_posts',
        id=id,
    ))
