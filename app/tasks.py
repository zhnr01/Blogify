"""Celery integration and background tasks.

The Celery app is created and bound to the Flask app in ``init_celery``. Tasks
run inside a Flask application context so they can use the ORM, mail, and config
exactly like request handlers do.

In the testing profile ``CELERY_TASK_ALWAYS_EAGER`` makes tasks run inline, so
no worker/broker is needed for tests.
"""
from celery import Celery, Task

celery_app = Celery(__name__)


def init_celery(app):
    """Configure Celery from Flask config and run tasks in an app context."""
    celery_app.conf.update(
        broker_url=app.config['CELERY_BROKER_URL'],
        result_backend=app.config['CELERY_RESULT_BACKEND'],
        task_always_eager=app.config.get('CELERY_TASK_ALWAYS_EAGER', False),
        task_ignore_result=True,
        broker_connection_retry_on_startup=True,
    )

    class ContextTask(Task):
        abstract = True

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return super().__call__(*args, **kwargs)

    celery_app.Task = ContextTask
    app.extensions['celery'] = celery_app
    return celery_app


@celery_app.task(name='app.tasks.send_email_task', max_retries=3, default_retry_delay=10)
def send_email_task(to, subject, template, **kwargs):
    """Render and send an email off the request thread."""
    # Imported here to avoid a circular import at module load time.
    from flask import current_app, render_template
    from flask_mail import Message

    from . import mail

    prefix = current_app.config['BLOGIFY_MAIL_SUBJECT_PREFIX']
    message = Message(
        f"{prefix} {subject}",
        sender=current_app.config['BLOGIFY_MAIL_SENDER'],
        recipients=[to],
    )
    message.body = render_template(f"{template}.txt", **kwargs)
    message.html = render_template(f"{template}.html", **kwargs)
    mail.send(message)
