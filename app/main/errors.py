from flask import jsonify, render_template, request

from . import main


def _wants_json():
    """True when the client prefers a JSON response over HTML."""
    accept = request.accept_mimetypes
    return accept.accept_json and not accept.accept_html


@main.app_errorhandler(404)
def page_not_found(e):
    if _wants_json():
        return jsonify({'error': 'not found'}), 404
    return render_template('404.html'), 404


@main.app_errorhandler(500)
def internal_server_error(e):
    if _wants_json():
        return jsonify({'error': 'internal server error'}), 500
    return render_template('500.html'), 500
