"""Database models and the domain permission scheme.

Roles map to bitmask permission sets; a user's role determines what actions
they may perform. Post/Comment bodies are rendered to sanitized HTML on write
via SQLAlchemy ``set`` events, with server-side syntax highlighting for code.
"""
import hashlib

import bleach
import pendulum
from bs4 import BeautifulSoup
from flask import current_app, url_for
from flask_login import AnonymousUserMixin, UserMixin
from itsdangerous import BadData, URLSafeTimedSerializer
from markdown import markdown
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name
from werkzeug.security import check_password_hash, generate_password_hash

from app.exceptions import ValidationError

from . import db, login_manager


class Permission:
    """Bitmask permission flags combined into role permission sets."""

    FOLLOW = 0x01
    COMMENT = 0x02
    WRITE = 0x04
    MODERATE_COMMENTS = 0x08
    ADMINISTER = 0x80


class Follow(db.Model):
    __tablename__ = 'follows'
    follower_id = db.Column(db.Integer, db.ForeignKey('users.id'),
                            primary_key=True)
    followed_id = db.Column(db.Integer, db.ForeignKey('users.id'),
                            primary_key=True)
    timestamp = db.Column(db.DateTime, default=pendulum.now)


class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=pendulum.now)
    disabled = db.Column(db.Boolean, default=False)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), index=True)

    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'code', 'em', 'i',
                        'strong', 'pre']
        target.body_html = bleach.linkify(bleach.clean(
            markdown(value or '', output_format='html'),
            tags=allowed_tags, strip=True))


db.event.listen(Comment.body, 'set', Comment.on_changed_body)


class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    permissions = db.Column(db.Integer)
    default = db.Column(db.Boolean, default=False, index=True)
    users = db.relationship('User', backref='role')

    def __repr__(self):
        return '<Role %r>' % self.name

    @staticmethod
    def insert_roles():
        """Create or update the built-in roles. Idempotent."""
        roles = {
            'User': (Permission.FOLLOW |
                     Permission.COMMENT |
                     Permission.WRITE, True),
            'Moderator': (Permission.FOLLOW |
                          Permission.COMMENT |
                          Permission.WRITE |
                          Permission.MODERATE_COMMENTS, False),
            'Administrator': (0xff, False),
        }
        for name, (permissions, default) in roles.items():
            role = Role.query.filter_by(name=name).first()
            if role is None:
                role = Role(name=name)
            role.permissions = permissions
            role.default = default
            db.session.add(role)
        db.session.commit()


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(64), unique=True, index=True)
    username = db.Column(db.String(64), unique=True, index=True)
    location = db.Column(db.String(64))
    about_me = db.Column(db.Text())
    member_since = db.Column(db.DateTime(), default=pendulum.now)
    last_seen = db.Column(db.DateTime(), default=pendulum.now)
    passwd_hash = db.Column(db.String(256))
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), index=True)
    confirmed = db.Column(db.Boolean, default=False)
    posts = db.relationship('Post', backref='author',
                            lazy='dynamic', cascade='all, delete-orphan')
    followed = db.relationship('Follow',
                               foreign_keys=[Follow.follower_id],
                               backref=db.backref('follower', lazy='joined'),
                               lazy='dynamic',
                               cascade='all, delete-orphan')
    followers = db.relationship('Follow',
                                foreign_keys=[Follow.followed_id],
                                backref=db.backref('followed', lazy='joined'),
                                lazy='dynamic',
                                cascade='all, delete-orphan')
    comments = db.relationship(
        'Comment', backref='author', lazy='dynamic', cascade='all, delete-orphan')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.role is None:
            if self.email is not None and \
                    self.email == current_app.config.get('BLOGIFY_ADMIN'):
                self.role = Role.query.filter_by(permissions=0xff).first()
            if self.role is None:
                self.role = Role.query.filter_by(default=True).first()

    # -- Serialization -----------------------------------------------------

    def to_json(self):
        return {
            'url': url_for('api.get_user', id=self.id, _external=True)
            if _endpoint_exists('api.get_user') else None,
            'username': self.username,
            'member_since': self.member_since,
            'last_seen': self.last_seen,
            'post_count': self.posts.count(),
        }

    # -- Tokens ------------------------------------------------------------

    def _serializer(self):
        return URLSafeTimedSerializer(current_app.config['SECRET_KEY'])

    def generate_auth_token(self, expiration=3600):
        """Return a signed, timestamped API token for this user."""
        return self._serializer().dumps({'id': self.id})

    @staticmethod
    def verify_auth_token(token, max_age=3600):
        """Return the User for a valid, unexpired token, else None."""
        serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        try:
            data = serializer.loads(token, max_age=max_age)
        except BadData:
            return None
        return db.session.get(User, data.get('id'))

    def generate_confirmation_token(self):
        return self._serializer().dumps({'confirm': self.id})

    def confirm(self, token, max_age=3600):
        try:
            data = self._serializer().loads(token, max_age=max_age)
        except BadData:
            return False
        if data.get('confirm') != self.id:
            return False
        self.confirmed = True
        db.session.add(self)
        db.session.commit()
        return True

    # -- Followers ---------------------------------------------------------

    @property
    def followed_posts(self):
        return Post.query.join(Follow, Follow.followed_id == Post.author_id)\
            .filter(Follow.follower_id == self.id)

    @staticmethod
    def add_self_follows():
        for user in User.query.all():
            if not user.is_following(user):
                user.follow(user)
                db.session.add(user)
        db.session.commit()

    def follow(self, user):
        if not self.is_following(user):
            db.session.add(Follow(follower=self, followed=user))

    def unfollow(self, user):
        f = self.followed.filter_by(followed_id=user.id).first()
        if f:
            db.session.delete(f)

    def is_following(self, user):
        if user.id is None:
            return False
        return self.followed.filter_by(followed_id=user.id).first() is not None

    def is_followed_by(self, user):
        if user.id is None:
            return False
        return self.followers.filter_by(follower_id=user.id).first() is not None

    # -- Misc --------------------------------------------------------------

    def gravatar(self, size=100, default='identicon', rating='g'):
        url = 'https://secure.gravatar.com/avatar'
        email_hash = hashlib.md5(self.email.lower().encode('utf-8')).hexdigest()
        return f'{url}/{email_hash}?s={size}&d={default}&r={rating}'

    def can(self, permissions):
        return self.role is not None and \
            (self.role.permissions & permissions) == permissions

    def is_administrator(self):
        return self.can(Permission.ADMINISTER)

    def ping(self):
        self.last_seen = pendulum.now(tz=pendulum.local_timezone())
        db.session.add(self)
        db.session.commit()

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.passwd_hash = generate_password_hash(password)

    def verify_passwd(self, password):
        return check_password_hash(self.passwd_hash, password)

    def __repr__(self):
        return '<User %r>' % self.username


@login_manager.user_loader
def load_user(user_id):
    """Flask-Login hook: load a user by id for the active session."""
    return db.session.get(User, int(user_id))


class AnonymousUser(AnonymousUserMixin):
    def can(self, permissions):
        return False

    def is_administrator(self):
        return False


class Post(db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(80))
    body = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=pendulum.now)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    body_html = db.Column(db.Text)
    comments = db.relationship(
        'Comment', backref='post', lazy='dynamic', cascade='all, delete-orphan')

    def to_json(self):
        return {
            'url': url_for('api.get_post', id=self.id, _external=True),
            'title': self.title,
            'body': self.body,
            'body_html': self.body_html,
            'timestamp': self.timestamp,
            'comment_count': self.comments.count(),
        }

    @staticmethod
    def from_json(json_post):
        """Build a Post from an API payload, validating required fields."""
        json_post = json_post or {}
        body = json_post.get('body')
        if not body:
            raise ValidationError('post does not have a body')
        return Post(title=json_post.get('title'), body=body)

    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        """Render markdown to HTML, syntax-highlighting any <pre language=...> blocks."""
        if not value:
            target.body_html = ''
            return

        formatter = HtmlFormatter(style='tango', noclasses=True, linenos=True)
        soup = BeautifulSoup(value, 'html.parser')
        rendered = str(soup)

        for pre in soup.find_all('pre'):
            language = pre.get('language')
            if not language:
                continue
            try:
                lexer = get_lexer_by_name(language.lower())
            except Exception:
                continue
            highlighted = highlight(pre.get_text().strip(), lexer, formatter)
            rendered = rendered.replace(str(pre).strip(), highlighted.strip())

        target.body_html = markdown(rendered, output_format='html')


db.event.listen(Post.body, 'set', Post.on_changed_body)


def _endpoint_exists(endpoint):
    """True if the given endpoint is registered on the current app."""
    return endpoint in current_app.view_functions
