from flask_wtf import FlaskForm
from wtforms import IntegerField, StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, Length, Regexp, EqualTo
from ..models import User
from wtforms import ValidationError


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Length(1, 64),
                                             Email()], render_kw={'style': 'margin-top: 15px;'})
    password = PasswordField('Password', validators=[DataRequired()],
                             render_kw={'style': 'margin-top: 15px;'})
    remember_me = BooleanField('Keep me logged in', render_kw={'style': 'margin-top: 15px;'})
    submit = SubmitField('Log In', render_kw={'style': 'margin-top: 15px;'})


class RegistrationForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Length(1, 64),
                                             Email()], render_kw={'style': 'margin-top: 15px;'})
    username = StringField('Username', validators=[
        DataRequired(), Length(1, 64), Regexp('^[A-Za-z][A-Za-z0-9_.]*$', 0,
                                              'Usernames must have only letters, '
                                              'numbers, dots or underscores')],
                                              render_kw={'style': 'margin-top: 15px;'})
    password = PasswordField('Password', validators=[
        DataRequired(), EqualTo('password2', message='Passwords must match.')],
        render_kw={'style': 'margin-top: 15px;'})
    password2 = PasswordField('Confirm password', validators=[DataRequired()],
                              render_kw={'style': 'margin-top: 15px;'})
    submit = SubmitField('Register', render_kw={'style': 'margin-top: 15px;'})

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered.')

    '''
    The methods starting with validate_* are called for validation similar to DataRequired()
    '''
    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('Username already in use.')


class PasswdChangeForm(FlaskForm):
    password = PasswordField('New Password', validators=[
        DataRequired(), EqualTo('password2', message='Passwords must match.')],
        render_kw={'style': 'margin-top: 15px;'})
    password2 = PasswordField('Confirm password', validators=[DataRequired()],
                              render_kw={'style': 'margin-top: 15px;'})
    submit = SubmitField('Change',render_kw={'style': 'margin-top: 15px;'})


class ChangeEmailForm(FlaskForm):
    email = StringField('New Email', validators=[DataRequired(), Length(1, 64),
                                             Email()], render_kw={'style': 'margin-top: 15px;'})
    submit = SubmitField('Change', render_kw={'style': 'margin-top: 15px;'})


class YesNoForm(FlaskForm):
    yes_button = SubmitField('Yes')
    no_button = SubmitField('No')