#!/usr/bin/env bash
# Container entrypoint. Selects a role based on the first argument:
#   web    -> run DB migrations + seed roles, then serve with Gunicorn
#   worker -> run a Celery worker
#   beat   -> run the Celery beat scheduler
# Any other value is executed verbatim (e.g. `bash` for debugging).
set -euo pipefail

role="${1:-web}"

case "$role" in
  web)
    echo "[entrypoint] applying database migrations..."
    flask db upgrade
    echo "[entrypoint] seeding roles..."
    flask deploy || true
    echo "[entrypoint] starting gunicorn..."
    exec gunicorn -c gunicorn.conf.py "manage:app"
    ;;
  worker)
    echo "[entrypoint] starting celery worker..."
    exec celery -A celery_worker.celery worker --loglevel=info
    ;;
  beat)
    echo "[entrypoint] starting celery beat..."
    exec celery -A celery_worker.celery beat --loglevel=info
    ;;
  *)
    exec "$@"
    ;;
esac
