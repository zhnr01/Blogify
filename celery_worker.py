"""Celery worker entrypoint.

Start a worker with::

    celery -A celery_worker.celery worker --loglevel=info

The Flask app is created so tasks run with full app context (config, ORM, mail).
"""
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from app import create_app
from app.tasks import celery_app as celery
from app.tasks import init_celery

app = create_app(os.getenv('FLASK_CONFIG') or 'default')
init_celery(app)

# Import task modules so the worker registers them.
import app.tasks  # noqa: E402,F401
