from flask import Flask
from flask_bootstrap import Bootstrap5
from flask_mail import Mail
from flask_sqlalchemy import SQLAlchemy

from config import config
from flask_login import LoginManager
from .helper import format_relative_time
from flask_pagedown import PageDown


bootstrap = Bootstrap5()
mail = Mail()

''' Moment() integrates the moment.js library to provide data and time features.
    It can display timestamps in real-time without reloading the pages.
'''

db = SQLAlchemy()
page_down = PageDown()

login_manager = LoginManager()
login_manager.session_protection = 'strong'
login_manager.login_view = 'auth.login'
from .models import AnonymousUser, Permission
login_manager.anonymous_user = AnonymousUser



def create_app(config_name='default'):
    app = Flask(__name__)
    '''
        It loads all the settings from the configuration object. For instance, if the configureation
        class contains the SECRET_KEY, then it will be used to configure the app(app.config['SECRET_KEY']='key')
    '''
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    bootstrap.init_app(app)
    mail.init_app(app)
    db.init_app(app)
    page_down.init_app(app)
    login_manager.init_app(app)

    from .main import main as main_blueprint
    from .auth import auth as auth_blueprint
    from .api import api as api_blueprint


    
    # Context processors make variables globally available to all templates. 
    # The below will make Permission class available to all templetes
    # Context processors make variables available to all templates during rendering
    @main_blueprint.app_context_processor
    def inject_permissions_and_time_conversion():
        return dict(Permission=Permission, format_relative_time=format_relative_time)

    
    '''
    When registering the blueprint with the main app using app.register_blueprint(auth_blueprint, url_prefix='/auth'), 
    the url_prefix parameter is set to '/auth'. This means that the route defined in the auth_blueprint will be 
    accessible under the '/auth' path.
    So, in this case, the login route would be accessible at the URL: http://yourdomain.com/auth/login
    '''
    app.register_blueprint(auth_blueprint, url_prefix='/auth')
    app.register_blueprint(main_blueprint)
    app.register_blueprint(api_blueprint, url_prefix='/api/v1')
    # attach routes and custom error pages here

    return app
