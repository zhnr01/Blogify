"""Observability: structured logging, request IDs, health checks, and metrics.

- Every request is assigned an ``X-Request-ID`` (honored from the inbound header
  if present) and it is attached to every log line for that request.
- Logs are emitted as single-line JSON so they can be shipped to and queried by
  a log aggregator.
- ``/healthz`` is a cheap liveness probe; ``/readyz`` checks the database so an
  orchestrator can gate traffic on real readiness.
- Prometheus metrics are exposed at ``/metrics`` when the exporter is installed.
"""
import logging
import time
import uuid

from flask import Blueprint, g, jsonify, request
from pythonjsonlogger import jsonlogger

from . import db

health = Blueprint('health', __name__)


class RequestIdFilter(logging.Filter):
    """Inject the current request id into every log record."""

    def filter(self, record):
        record.request_id = getattr(g, 'request_id', '-') if _in_request() else '-'
        return True


def _in_request():
    try:
        return bool(request)
    except Exception:
        return False


def _configure_logging(app):
    handler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter(
        '%(asctime)s %(levelname)s %(name)s %(message)s %(request_id)s',
        rename_fields={'asctime': 'timestamp', 'levelname': 'level'},
    )
    handler.setFormatter(formatter)
    handler.addFilter(RequestIdFilter())

    level = logging.DEBUG if app.debug else logging.INFO
    # Replace default handlers so we don't double-log.
    app.logger.handlers = [handler]
    app.logger.setLevel(level)

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)


def _register_request_hooks(app):
    @app.before_request
    def _start_timer_and_request_id():
        g.request_id = request.headers.get('X-Request-ID') or uuid.uuid4().hex
        g.request_start = time.perf_counter()

    @app.after_request
    def _log_request(response):
        response.headers['X-Request-ID'] = getattr(g, 'request_id', '-')
        duration_ms = None
        if hasattr(g, 'request_start'):
            duration_ms = round((time.perf_counter() - g.request_start) * 1000, 2)
        app.logger.info(
            'request',
            extra={
                'method': request.method,
                'path': request.path,
                'status': response.status_code,
                'duration_ms': duration_ms,
                'remote_addr': request.remote_addr,
            },
        )
        return response


@health.route('/healthz')
def healthz():
    """Liveness: the process is up and can serve requests."""
    return jsonify({'status': 'ok'})


@health.route('/readyz')
def readyz():
    """Readiness: dependencies (the database) are reachable."""
    try:
        db.session.execute(db.text('SELECT 1'))
    except Exception as exc:  # pragma: no cover - exercised via integration
        return jsonify({'status': 'unavailable', 'error': str(exc)}), 503
    return jsonify({'status': 'ready'})


def init_observability(app):
    """Wire logging, request hooks, health endpoints, and metrics."""
    _configure_logging(app)
    _register_request_hooks(app)
    app.register_blueprint(health)

    # Optional Prometheus metrics at /metrics.
    try:
        from prometheus_flask_exporter import PrometheusMetrics
        metrics = PrometheusMetrics(app, group_by='endpoint')
        metrics.info('blogify_app_info', 'Application info', version='1.0.0')
    except Exception:  # exporter missing or already registered
        pass
