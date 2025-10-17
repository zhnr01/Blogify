from flask import render_template
from flask_mail import Message
from . import mail


def send_email(to, subject, template, **kwargs):

    msg = Message(subject, recipients=[to], sender='username')

    msg.body = render_template(f"{template}.txt", **kwargs)
    msg.html = render_template(f"{template}.html", **kwargs)
    mail.send(msg)
    