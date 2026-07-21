"""Shared pagination envelope for API list endpoints."""
from flask import request, url_for


def paginate(pagination, items, endpoint, **url_args):
    """Wrap a Flask-SQLAlchemy pagination object in a standard JSON envelope."""
    prev_url = None
    if pagination.has_prev:
        prev_url = url_for(endpoint, page=pagination.page - 1,
                           _external=True, **url_args)
    next_url = None
    if pagination.has_next:
        next_url = url_for(endpoint, page=pagination.page + 1,
                           _external=True, **url_args)
    return {
        'items': items,
        'meta': {
            'page': pagination.page,
            'per_page': pagination.per_page,
            'total': pagination.total,
            'pages': pagination.pages,
            'prev_url': prev_url,
            'next_url': next_url,
        },
    }


def page_arg():
    """Read the ``page`` query parameter, defaulting to 1."""
    return request.args.get('page', 1, type=int)
