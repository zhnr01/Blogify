from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField, BooleanField, SelectField, ValidationError
from wtforms.validators import Length, DataRequired, Email, Regexp
from ..models import Role, User
from flask_pagedown.fields import PageDownField


class EditProfileForm(FlaskForm):
    name = StringField('Real name', validators=[Length(0, 64)], render_kw={
                       'style': 'margin-top: 15px;'})
    location = StringField('Location', validators=[Length(
        0, 64)], render_kw={'style': 'margin-top: 15px;'})
    about_me = TextAreaField('About me', render_kw={'style': 'height: 240px; margin-top: 15px;'})
    submit = SubmitField('Submit', render_kw={'style': 'margin-top: 15px;'})


class CommentForm(FlaskForm):
    body = StringField('', validators=[DataRequired()])
    submit = SubmitField('Submit', render_kw={'style': 'margin-top: 15px;'})


class EditProfileAdminForm(FlaskForm):

    email = StringField('Email', validators=[DataRequired(), Length(1, 64),
                                             Email()], render_kw={'style': 'margin-top: 15px;'})
    username = StringField('Username', validators=[
        DataRequired(), Length(1, 64), Regexp('^[A-Za-z][A-Za-z0-9_.]*$', 0,
                                              'Usernames must have only letters, '
                                              'numbers, dots or underscores')], render_kw={'style': 'margin-top: 15px;'})
    confirmed = BooleanField('Confirmed')
    role = SelectField('Role', coerce=int, render_kw={
                       'style': 'margin-top: 15px;'})
    name = StringField('Real name', validators=[Length(0, 64)], render_kw={
                       'style': 'margin-top: 15px;'})
    location = StringField('Location', validators=[Length(
        0, 64)], render_kw={'style': 'margin-top: 15px;'})
    about_me = TextAreaField('About me', render_kw={
                             'style': 'margin-top: 15px;'})
    submit = SubmitField('Submit', render_kw={'style': 'margin-top: 15px;'})

    def __init__(self, user, *args, **kwargs):
        super(EditProfileAdminForm, self).__init__(*args, **kwargs)
        self.role.choices = [(role.id, role.name)
                             for role in Role.query.order_by(Role.name).all()]
        self.user = user

    '''
        Any functions of the form 'validate_fieldName' will be called as validators on those fields.
    '''

    def validate_email(self, field):
        if field.data != self.user.email and \
                User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered.')

    def validate_username(self, field):
        if field.data != self.user.username and \
                User.query.filter_by(username=field.data).first():
            raise ValidationError('Username already in use.')


class PostForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(1, 64)])
    '''
        PageDown, a client-side Markdown-to-HTML converter implemented in Java-
        Script.

        The markdown preview is added with the help of PageDown libraries so these
        must be added to the html file. Fortunately, have a macro that adds all the
        required files for us. So add this to your base template file'S script area.
        {{ pagedown.include_pagedown() }}
    '''
    body = PageDownField("What's on your mind?", validators=[DataRequired()],
                         render_kw={'style': 'height: 400px; margin-top: 15px;'})
    submit = SubmitField('Post', render_kw={'style': 'margin-top: 15px;'})
