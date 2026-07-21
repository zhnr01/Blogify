"""Application factory and extension wiring.

Extensions are instantiated at module scope but bound to the app inside
``create_app`` so the app can be created multiple times (tests, workers, CLI)
with different configuration.
"""
# --- Extensions (unbound) --------------------------------------------------
# Imported here so the rest of the app can do ``from app import db`` etc.
from flask import Flask
from flask_caching import Cache
from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate
from flask_pagedown import PageDown
from flask_sqlalchemy import SQLAlchemy

from config import config

from .helper import format_relative_time

try:
    from flask_bootstrap import Bootstrap5
except ImportError:  # package name is bootstrap_flask in some envs
    Bootstrap5 = None

db = SQLAlchemy()
migrate = Migrate()
mail = Mail()
cache = Cache()
page_down = PageDown()
bootstrap = Bootstrap5() if Bootstrap5 else None

login_manager = LoginManager()
login_manager.session_protection = "strong"
login_manager.login_view = "auth.login"

from .models import AnonymousUser, Permission  # noqa: E402

login_manager.anonymous_user = AnonymousUser


def create_app(config_name="default"):
    """Build and configure a Flask application instance."""
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    # Bind extensions to this app instance.
    db.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    cache.init_app(app)
    page_down.init_app(app)
    login_manager.init_app(app)
    if bootstrap is not None:
        bootstrap.init_app(app)

    _register_blueprints(app)
    _register_context_processors(app)

    # Rate limiting, CSRF, and security headers. Registered after blueprints so
    # the API blueprint exists to be exempted from session CSRF.
    from .security import init_security
    init_security(app)

    # Structured logging, request IDs, health/readiness endpoints, metrics.
    from .observability import init_observability
    init_observability(app)

    # Background jobs (Celery). Email and other slow work run off-thread.
    from .tasks import init_celery
    init_celery(app)

    return app


def _register_blueprints(app):
    from .api import api as api_blueprint
    from .auth import auth as auth_blueprint
    from .main import main as main_blueprint

    app.register_blueprint(main_blueprint)
    app.register_blueprint(auth_blueprint, url_prefix="/auth")
    app.register_blueprint(api_blueprint, url_prefix="/api/v1")


def _register_context_processors(app):
    @app.context_processor
    def inject_globals():
        return dict(Permission=Permission,
                    format_relative_time=format_relative_time)
