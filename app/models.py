import hashlib
import bleach
from markdown import markdown
import pendulum
from flask import current_app, url_for

from app.exceptions import ValidationError
from . import db
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import TimedSerializer as Serializer
from flask_login import AnonymousUserMixin, UserMixin
from . import login_manager
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter
from bs4 import BeautifulSoup
from pygments.lexers import guess_lexer

class Permission:
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


'''
    Index
    -----
        An index is essentially a data structure that provides a quick way to 
        look up records in a table based on the values in one or more columns.

    Indexing can make the filtering, sorting, and lookup of values a lot more easier.
    We should index those columns that we use to filter data or sort data while
    querying.

    EXAMPLE:    
        User.query.filter_by(username='john').first()

    In the above example we are using the username to filter a User object so making this 
    column indexed is useful for faster querying.

    NOW, the index data structure can a B-Tree which looks something like 
                                
                                +------------------------+
                                |         [D, David]      |
                                +------------------------+
                            /                             \
        +------------------------+              +------------------------+
        |     [B, Bob]            |              |      [F, Frank]         |
        +------------------------+              +------------------------+
        /               \                           /                \
    +----------------+ +----------------+   +----------------+ +----------------+
    | [A, Alice]     | | [C, Charlie]   |   | [E, Eva]       | | [G, Grace]      |
    +----------------+ +----------------+   +----------------+ +----------------+

    The above is the index of the username column.


    JOIN
    ----
        A join is used to retrieve data from more than one table based on the conditions.

    lazy Option
    -----------
    In SQLAlchemy, including Flask-SQLAlchemy, "lazy loading" refers 
    to how relationships between tables are loaded. By default, relationships 
    are lazy-loaded, which means that the related data 
    is only loaded from the database when you access the attribute.


    Lazy loading(default):
    ---------------------
    class User(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        posts = db.relationship('Post', lazy='select')

    In this example, lazy='select' is the default behavior. It means 
    that when you access the posts attribute of a User instance, 
    a separate SELECT query will be executed to fetch the related Post objects.

    Eager loading:
    -------------
    You can change the lazy-loading behavior to "eager loading," 
    which means that the related data is loaded at the same time as the main query.

    class User(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        posts = db.relationship('Post', lazy='joined')

    In this case, if you retrieve a User instance, the 
    related Post instances will be loaded with a JOIN query

    Disable loading
    ---------------
    If you want to disable lazy loading entirely and always 
    fetch the related data, you can use lazy='dynamic'.
    This returns a query object that you can further refine.

    class User(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        posts = db.relationship('Post', lazy='dynamic')


        
'''


class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=pendulum.now)
    disabled = db.Column(db.Boolean)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'))

    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'code', 'em', 'i',
                        'strong', 'pre']
        target.body_html = bleach.linkify(bleach.clean(
            markdown(value, output_format='html'),
            tags=allowed_tags, strip=True))


db.event.listen(Comment.body, 'set', Comment.on_changed_body)


class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
    permissions = db.Column(db.Integer)
    default = db.Column(db.Boolean, default=False, index=True)
    users = db.relationship('User', backref='role')

    def __repr__(self):
        return '<Role %r>' % self.name

    @staticmethod
    def insert_roles():
        roles = {
            'User': (Permission.FOLLOW |
                     Permission.COMMENT |
                     Permission.WRITE_ARTICLES, True),
            'Moderator': (Permission.FOLLOW |
                          Permission.COMMENT |
                          Permission.WRITE_ARTICLES |
                          Permission.MODERATE_COMMENTS, False),
            'Administrator': (0xff, False)
        }
        for r in roles:
            role = Role.query.filter_by(name=r).first()
            if role is None:
                role = Role(name=r)
            role.permissions = roles[r][0]
            role.default = roles[r][1]
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
    passwd_hash = db.Column(db.String(128))
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
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
        super(User, self).__init__(**kwargs)
        if self.role is None:
            if self.email == current_app.config['FLASKY_ADMIN']:
                self.role = Role.query.filter_by(permissions=0xff).first()
            if self.role is None:
                self.role = Role.query.filter_by(default=True).first()

    def to_json(self):
        json_user = {
        #'url': url_for('api.get_user', id=self.id),
        'username': self.username,
        'member_since': self.member_since,
        'last_seen': self.last_seen,
        #'posts_url': url_for('api.get_user_posts', id=self.id),
        #'followed_posts_url': url_for('api.get_user_followed_posts',
        #id=self.id),
        'post_count': self.posts.count()
        }
        return json_user
    
    @staticmethod
    def from_json(json_post):
        body = json_post.get('body')
        if body is None or body == '':
            raise ValidationError('post does not have a body')
        return Post(body=body)
    
    def generate_auth_token(self, expiration):
        s = Serializer(current_app.config['SECRET_KEY'],
        expires_in=expiration)
        return s.dumps({'id': self.id}).decode('utf-8')

    @staticmethod
    def verify_auth_token(token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return None
        return User.query.get(data['id'])

    
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

    def gravatar(self, size=100, default='identicon', rating='g'):
        url = 'https://secure.gravatar.com/avatar'
        hash = hashlib.md5(self.email.lower().encode('utf-8')).hexdigest()
        return '{url}/{hash}?s={size}&d={default}&r={rating}'.format(
            url=url, hash=hash, size=size, default=default, rating=rating)

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
        raise AttributeError('password is not readable attribute')

    @password.setter
    def password(self, password):
        self.passwd_hash = generate_password_hash(password)

    def __repr__(self):
        return '<User %r>' % self.username

    def verify_passwd(self, password):
        return check_password_hash(self.passwd_hash, password)

    '''
        Flask-login requires the application to designate this function which will take a user_id
        as a string. The @login_manger.user_loader decorator will register this function to get 
        called when the flask-login needs to get the information about the logged in user from 
        the database.
    '''
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    def generate_confirmation_token(self):
        s = Serializer(current_app.config['SECRET_KEY'])
        return s.dumps({'confirm': self.id})

    def confirm(self, token, max_age=3600):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token, max_age=max_age)
        except:
            return False

        if data.get('confirm') != self.id:
            return False
        self.confirmed = True
        db.session.add(self)
        db.session.commit()
        return True

    def follow(self, user):
        if not self.is_following(user):
            f = Follow(follower=self, followed=user)
            db.session.add(f)

    def unfollow(self, user):
        f = self.followed.filter_by(followed_id=user.id).first()
        if f:
            db.session.delete(f)

    def is_following(self, user):
        if user.id is None:
            return False
        return self.followed.filter_by(
            followed_id=user.id).first() is not None

    def is_followed_by(self, user):
        if user.id is None:
            return False
        return self.followers.filter_by(
            follower_id=user.id).first() is not None


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
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    body_html = db.Column(db.Text)
    comments = db.relationship(
        'Comment', backref='post', lazy='dynamic', cascade='all, delete-orphan')


    def to_json(self):
        json_post = {
        'url': url_for('api.get_post', id=self.id),
        'body': self.body,
        'body_html': self.body_html,
        'timestamp': self.timestamp,
        #'author_url': url_for('api.get_user', id=self.author_id),
        #'comments_url': url_for('api.get_post_comments', id=self.id),
        'comment_count': self.comments.count()
        }
        return json_post

    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        formatter = HtmlFormatter(style='tango', noclasses=True, lineos=True)
        # allowed_tags = ['a', 'abbr', 'acronym', 'b', 'blockquote', 'code',
        #                 'em', 'i', 'li', 'ol', 'pre', 'strong', 'ul',
        #                 'h1', 'h2', 'h3', 'p', 'img', 'div', 'span']
        # allowed_attrs = {'img': ['src', 'alt']}
        
        body_html = value
        soup = BeautifulSoup(body_html, 'html.parser')
        pre_elements = soup.find_all('pre')
        string_soup = str(soup)
        
        for pre_element in pre_elements:
            language = pre_element['language']
            lexer = get_lexer_by_name(language.lower())

            code = pre_element.get_text().strip()

            modified_code = highlight(code, lexer, formatter)
            string_soup = string_soup.replace(str(pre_element).strip(), modified_code.strip())
        
        target.body_html =  markdown(string_soup, format='html')


db.event.listen(Post.body, 'set', Post.on_changed_body)
