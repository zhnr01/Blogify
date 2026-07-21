"""Email helpers.

Sending is dispatched to a Celery worker so it never blocks the request thread.
Under the testing profile (``CELERY_TASK_ALWAYS_EAGER``) the task runs inline.
If Celery/broker wiring is unavailable, we fall back to sending synchronously so
local development without a broker still works.
"""
from flask import current_app, render_template
from flask_mail import Message

from . import mail
from .tasks import send_email_task


def send_email(to, subject, template, **kwargs):
    """Queue an email for delivery (async via Celery, sync as a fallback)."""
    try:
        return send_email_task.delay(to, subject, template, **kwargs)
    except Exception:
        current_app.logger.warning(
            'Celery dispatch failed; sending email synchronously', exc_info=True)
        return _send_sync(to, subject, template, **kwargs)


def _send_sync(to, subject, template, **kwargs):
    prefix = current_app.config['BLOGIFY_MAIL_SUBJECT_PREFIX']
    message = Message(
        f"{prefix} {subject}",
        sender=current_app.config['BLOGIFY_MAIL_SENDER'],
        recipients=[to],
    )
    message.body = render_template(f"{template}.txt", **kwargs)
    message.html = render_template(f"{template}.html", **kwargs)
    mail.send(message)
