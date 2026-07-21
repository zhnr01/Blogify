"""Application entrypoint and management commands.

Run the dev server with ``flask run`` (FLASK_APP=manage.py) or execute this
module directly. Loads a local .env file if python-dotenv is available.
"""
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:  # dotenv is optional in production images
    pass

from flask_migrate import Migrate

from app import create_app, db
from app.models import Comment, Follow, Permission, Post, Role, User

app = create_app(os.getenv('FLASK_CONFIG') or 'default')
migrate = Migrate(app, db)


@app.shell_context_processor
def make_shell_context():
    return dict(db=db, User=User, Role=Role, Permission=Permission,
                Post=Post, Comment=Comment, Follow=Follow)


@app.cli.command('test')
def test():
    """Run the unit tests."""
    import pytest
    raise SystemExit(pytest.main(['-q']))


@app.cli.command('deploy')
def deploy():
    """Run deployment tasks: migrate to head and seed built-in roles."""
    from flask_migrate import upgrade
    upgrade()
    Role.insert_roles()


if __name__ == '__main__':
    app.run(host=os.getenv('HOST', '127.0.0.1'),
            port=int(os.getenv('PORT', '5000')),
            debug=app.config.get('DEBUG', False))
