"""Application configuration (12-factor).

All environment-specific values and secrets are read from environment variables
so nothing sensitive is hard-coded. In development sensible localhost defaults
are provided; in production the required secrets must be supplied via the
environment or the app refuses to start.
"""
import os

base_dir = os.path.abspath(os.path.dirname(__file__))


def _bool(name: str, default: bool = False) -> bool:
    """Parse a boolean environment variable."""
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Config:
    """Settings shared across every environment."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")

    # SQLAlchemy
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,          # detect dropped connections before use
        "pool_recycle": 1800,           # recycle connections every 30 min
    }

    # Mail
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.googlemail.com")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", "587"))
    MAIL_USE_TLS = _bool("MAIL_USE_TLS", True)
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    BLOGIFY_MAIL_SUBJECT_PREFIX = "[Blogify]"
    BLOGIFY_MAIL_SENDER = os.environ.get("BLOGIFY_MAIL_SENDER", "Blogify <no-reply@blogify.local>")
    BLOGIFY_ADMIN = os.environ.get("BLOGIFY_ADMIN")

    # Pagination
    BLOGIFY_POSTS_PER_PAGE = int(os.environ.get("BLOGIFY_POSTS_PER_PAGE", "5"))
    BLOGIFY_COMMENTS_PER_PAGE = int(os.environ.get("BLOGIFY_COMMENTS_PER_PAGE", "5"))

    # Redis / cache / Celery
    REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    CACHE_TYPE = os.environ.get("CACHE_TYPE", "SimpleCache")
    CACHE_DEFAULT_TIMEOUT = int(os.environ.get("CACHE_DEFAULT_TIMEOUT", "60"))
    CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", os.environ.get("REDIS_URL", "redis://localhost:6379/0"))
    CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", os.environ.get("REDIS_URL", "redis://localhost:6379/1"))

    # Rate limiting
    RATELIMIT_ENABLED = _bool("RATELIMIT_ENABLED", True)
    RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URI", os.environ.get("REDIS_URL", "memory://"))
    RATELIMIT_DEFAULT = os.environ.get("RATELIMIT_DEFAULT", "200 per hour")
    RATELIMIT_HEADERS_ENABLED = True

    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get("DEV_DATABASE_URL") or \
        "sqlite:///" + os.path.join(base_dir, "data-dev.sqlite")
    # SimpleCache in dev so Redis is not required to run locally.
    CACHE_TYPE = os.environ.get("CACHE_TYPE", "SimpleCache")


class TestingConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = os.environ.get("TEST_DATABASE_URL") or "sqlite://"
    CACHE_TYPE = "NullCache"
    # Run Celery tasks synchronously in tests instead of dispatching to a worker.
    CELERY_TASK_ALWAYS_EAGER = True
    RATELIMIT_ENABLED = False


class ProductionConfig(Config):
    # Postgres in production; DATABASE_URL is required.
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    CACHE_TYPE = os.environ.get("CACHE_TYPE", "RedisCache")

    SQLALCHEMY_ENGINE_OPTIONS = {
        **Config.SQLALCHEMY_ENGINE_OPTIONS,
        "pool_size": int(os.environ.get("SQLALCHEMY_POOL_SIZE", "10")),
        "max_overflow": int(os.environ.get("SQLALCHEMY_MAX_OVERFLOW", "20")),
    }

    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        # Fail fast if critical secrets/URLs are missing in production.
        required = {
            "SECRET_KEY": os.environ.get("SECRET_KEY"),
            "DATABASE_URL": os.environ.get("DATABASE_URL"),
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise RuntimeError(
                "Missing required production environment variables: "
                + ", ".join(missing)
            )


config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
