# Architecture

This document explains how Blogify is put together and the reasoning behind the
main decisions. For setup and usage, see the [README](../README.md).

## Design goals

1. **Keep request handlers thin.** Views and API resources parse input and
   render output; all business logic and database writes live in a service
   layer. This makes the rules testable without HTTP and keeps the two
   presentation surfaces (HTML and JSON) consistent.
2. **Configuration over code.** Everything environment-specific comes from
   environment variables (12-factor), with dev/testing/production profiles.
   Production fails fast if required secrets are missing.
3. **Operable by default.** Structured logs, request correlation IDs, health and
   readiness probes, and metrics are built in, not bolted on.
4. **Deployable as-is.** A multi-stage image, a Gunicorn config, and a compose
   stack (web + worker + Postgres + Redis) ship in the repo.

## System overview

```
                         ┌─────────────────────────────┐
        HTTP clients ───▶│         Gunicorn            │
   (browser / API)       │   (gthread workers)          │
                         └──────────────┬──────────────┘
                                        │
                         ┌──────────────▼──────────────┐
                         │        Flask app             │
                         │  ┌────────────────────────┐  │
                         │  │ main (HTML)  api (JSON)  │  │  ← thin handlers
                         │  ├────────────────────────┤  │
   security ────────────┼─▶│      service layer       │  │  ← business logic
   (CSRF, rate limit,    │  │   (posts, comments)      │  │
    headers)             │  ├──────────┬──────────────┤  │
   observability ────────┼─▶│  models  │  schemas      │  │
   (logs, /healthz,      │  └──────────┼──────────────┘  │
    /readyz, /metrics)   └─────────────┼─────────────────┘
                                       │
                    ┌──────────────────┼───────────────────┐
                    ▼                   ▼                    ▼
              ┌───────────┐      ┌───────────┐        ┌───────────┐
              │ Postgres  │      │   Redis    │        │  Celery   │
              │ (pooled)  │      │ cache +    │◀──────▶│  worker   │
              │           │      │ broker +   │  jobs  │ (email)   │
              │           │      │ ratelimit  │        │           │
              └───────────┘      └───────────┘        └───────────┘
```

Redis is used for three independent concerns on separate logical databases:
the feed cache, the Celery broker/result backend, and the rate-limit store.

## Layers

### Presentation — `app/main`, `app/api`

`main` renders Jinja templates for the browser; `api` is a versioned REST
surface mounted at `/api/v1`. Both are intentionally thin: they authenticate,
validate input (via schemas for the API), call a service, and format the
response. The API returns a consistent envelope for lists
(`items` + `meta`) and errors (`error` + `message`), and never leaks stack
traces.

### Services — `app/services`

The only place that mutates domain state. `create_post`, `update_post`,
`create_comment`, moderation toggles, and the cached feed reads all live here.
Because services take plain arguments and return models, they are unit-tested
directly without spinning up a request.

### Data — `app/models.py`, `app/schemas.py`

SQLAlchemy models define the schema and the bitmask permission system (roles map
to permission sets). Post/comment bodies are sanitized and rendered to HTML on
write via SQLAlchemy `set` events, with Pygments highlighting fenced code.
Marshmallow schemas are the single source of truth for API payload shape and
validation.

### Cross-cutting — `app/security.py`, `app/observability.py`, `app/tasks.py`

Wired into the app inside `create_app` so a fresh, fully-configured app can be
built for tests, workers, and the CLI.

## Key mechanisms

### Authentication & authorization

- Browser sessions use Flask-Login. The API uses HTTP basic auth with either
  email+password or a signed, expiring token (itsdangerous) passed as the
  username.
- Roles carry a permission bitmask (`FOLLOW`, `COMMENT`, `WRITE`,
  `MODERATE_COMMENTS`, `ADMINISTER`). Endpoints guard on the specific permission
  they need, so a user without `COMMENT` gets a 403 rather than silently
  succeeding.

### Caching & invalidation

The post feed is cached under a **version-stamped key**
(`posts:feed:v{N}:p{page}:s{size}`). Any create/update bumps the version, which
invalidates every cached page at once without enumerating keys. Cache backend
failures are swallowed so a Redis hiccup can never break a read or write path.

### Background work

Email is dispatched to Celery (`send_email_task.delay(...)`) so the request
thread never blocks on SMTP. Tasks run inside a Flask app context via a custom
`ContextTask`, so they use the ORM, mail, and config exactly like a request. In
the testing profile tasks run eagerly, so no broker is needed for tests; if
dispatch fails in local dev, email falls back to sending synchronously.

### Observability

Every request gets an `X-Request-ID` (honored from the inbound header if
present, echoed back on the response) that is attached to every JSON log line,
so logs for one request can be correlated across the app and worker. `/healthz`
is a cheap liveness probe; `/readyz` checks the database so an orchestrator can
gate traffic on real readiness. Prometheus metrics are exposed at `/metrics`.

## Data model

```
User ──< Post ──< Comment
  │        │         │
  │        └─────────┘  (author_id, post_id — both indexed)
  │
  └──< Follow >── User   (self-referential many-to-many)
  │
Role ──< User            (role_id indexed; permissions bitmask)
```

Foreign keys used in joins and filters are indexed (`posts.author_id`,
`comments.author_id`, `comments.post_id`, `users.role_id`), alongside the
existing timestamp and unique email/username indexes. Schema changes are managed
with Alembic migrations.

## Configuration profiles

| Profile | Database | Cache | Celery | Rate limit |
|---------|----------|-------|--------|------------|
| development | SQLite | SimpleCache (in-proc) | real (or sync fallback) | on |
| testing | in-memory SQLite | NullCache | eager (inline) | off |
| production | Postgres (pooled) | Redis | Redis broker/worker | Redis |

Production validates that `SECRET_KEY` and `DATABASE_URL` are present at startup
and refuses to boot otherwise.

## Deployment

The `Dockerfile` builds dependencies into a virtualenv in a builder stage, then
copies just the venv into a slim runtime image that runs as a non-root user with
a container `HEALTHCHECK`. `docker-entrypoint.sh` selects a role — `web` runs
migrations and seeds roles before starting Gunicorn; `worker`/`beat` start
Celery. `docker-compose.yml` wires web, worker, Postgres, and Redis together
with health-gated startup.

## Limitations / next steps

- Token auth is bearer-in-basic; a dedicated `Authorization: Bearer` scheme and
  refresh tokens would be a natural upgrade.
- No full-text search yet; post listing is chronological.
- Metrics are exposed but no dashboards/alerts are bundled.
