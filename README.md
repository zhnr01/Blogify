# Blogify

A production-grade blogging platform built with Flask — server-rendered UI plus a
versioned REST API, layered architecture, background jobs, caching, observability,
and a containerized deployment stack.

Blogify started as a Flask-tutorial project and was hardened into a deployable
service: 12-factor config, a service layer, schema-validated APIs, rate limiting
and security headers, Postgres with connection pooling, Redis caching, Celery
workers, structured logging with health checks and metrics, a test suite, and CI.

## Features

- **Accounts & authz** — registration, email confirmation, login sessions
  (Flask-Login), and a role/permission scheme (User, Moderator, Administrator).
- **Content** — Markdown posts with server-side syntax highlighting, comments,
  following, and comment moderation.
- **REST API** (`/api/v1`) — token or HTTP-basic auth, marshmallow-validated
  payloads, consistent JSON error envelopes, and paginated list responses.
- **Security** — CSRF-protected forms, per-route rate limiting, and security
  response headers (X-Frame-Options, X-Content-Type-Options, HSTS, etc.).
- **Performance** — Redis caching of the post feed with version-based
  invalidation; indexed foreign keys; pooled DB connections.
- **Async** — email delivery offloaded to Celery workers.
- **Ops** — JSON logs with per-request IDs, `/healthz` + `/readyz` probes,
  Prometheus metrics at `/metrics`, and a multi-stage Docker image.

## Architecture

Requests flow through thin view/API handlers into a service layer that owns all
business logic and database writes. See
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full breakdown and
diagram.

```
app/
├── __init__.py        # application factory + extension wiring
├── config.py          # (repo root) 12-factor config: dev / testing / production
├── models.py          # SQLAlchemy models + permission scheme
├── schemas.py         # marshmallow (de)serialization + validation
├── security.py        # CSRF, rate limiting, security headers
├── observability.py   # JSON logging, request IDs, health checks, metrics
├── tasks.py           # Celery app + background tasks (email)
├── services/          # business logic (posts, comments) — the only DB writers
├── api/               # versioned REST API (auth, posts, comments, users)
├── auth/              # session auth views + forms
├── main/              # server-rendered blog views + forms
└── templates/         # Jinja2 templates
```

## Getting started (local)

Requires Python 3.10+.

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env        # then edit values

export FLASK_APP=manage.py FLASK_CONFIG=development
flask db upgrade            # create schema
flask deploy               # run migrations + seed roles
flask run
```

The dev profile uses SQLite and an in-process cache, so neither Postgres nor
Redis is required to run locally.

## Running with Docker

The compose stack runs the web app, a Celery worker, Postgres, and Redis:

```bash
export SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
docker compose up --build
```

The web container applies migrations and seeds roles on start, then serves via
Gunicorn on port 8000. Health check: `curl localhost:8000/healthz`.

## REST API

Authenticate with HTTP basic (email + password) or a bearer-style token used as
the basic-auth username.

```bash
# Get a token
curl -X POST -u you@example.com:password http://localhost:8000/api/v1/tokens/

# Create a post using the token
curl -X POST -u "$TOKEN:" -H 'Content-Type: application/json' \
  -d '{"title":"Hello","body":"My first post"}' \
  http://localhost:8000/api/v1/posts/
```

Selected endpoints:

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/tokens/` | Issue an auth token (basic auth only) |
| GET | `/api/v1/posts/` | List posts (paginated) |
| POST | `/api/v1/posts/` | Create a post (requires WRITE) |
| GET | `/api/v1/posts/<id>` | Fetch a post |
| PUT | `/api/v1/posts/<id>` | Edit a post (author/admin) |
| GET | `/api/v1/posts/<id>/comments/` | List a post's comments |
| POST | `/api/v1/posts/<id>/comments/` | Comment (requires COMMENT) |
| GET | `/api/v1/users/<id>` | Public user profile |

List responses use `{ "items": [...], "meta": { page, per_page, total, pages, prev_url, next_url } }`.
Errors use `{ "error": "<slug>", "message": "...", ... }`.

## Configuration

All settings come from environment variables (see `.env.example`). Production
requires `SECRET_KEY` and `DATABASE_URL` or the app refuses to start. Key
variables: `FLASK_CONFIG`, `DATABASE_URL`, `REDIS_URL`, `CELERY_BROKER_URL`,
`RATELIMIT_STORAGE_URI`, `MAIL_*`, `BLOGIFY_ADMIN`.

## Testing & quality

```bash
pytest                 # or: flask test
pytest --cov=app       # with coverage
ruff check .           # lint
```

CI (GitHub Actions) runs ruff, the pytest matrix on Python 3.10–3.12, and a
Docker build on every push and PR.

## License

MIT.
