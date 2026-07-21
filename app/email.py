"""Email helpers.

The sender and subject prefix come from configuration rather than being
hard-coded. Sending is moved off the request thread to a Celery task in a later
stage; for now it is synchronous.
"""
from flask import current_app, render_template
from flask_mail import Message

from . import mail


def send_email(to, subject, template, **kwargs):
    """Render the given template pair and send the email."""
    app = current_app
    subject = f"{app.config['BLOGIFY_MAIL_SUBJECT_PREFIX']} {subject}"
    message = Message(
        subject,
        sender=app.config['BLOGIFY_MAIL_SENDER'],
        recipients=[to],
    )
    message.body = render_template(f"{template}.txt", **kwargs)
    message.html = render_template(f"{template}.html", **kwargs)
    mail.send(message)
