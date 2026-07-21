"""Gunicorn configuration.

Worker count defaults to (2*CPU)+1 but can be overridden with WEB_CONCURRENCY.
Logs go to stdout/stderr so the container runtime can collect them.
"""
import multiprocessing
import os

bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"
workers = int(os.getenv("WEB_CONCURRENCY", (multiprocessing.cpu_count() * 2) + 1))
worker_class = os.getenv("GUNICORN_WORKER_CLASS", "gthread")
threads = int(os.getenv("GUNICORN_THREADS", "4"))
timeout = int(os.getenv("GUNICORN_TIMEOUT", "30"))
graceful_timeout = 30
keepalive = 5
max_requests = 1000
max_requests_jitter = 100

accesslog = "-"
errorlog = "-"
loglevel = os.getenv("GUNICORN_LOG_LEVEL", "info")
