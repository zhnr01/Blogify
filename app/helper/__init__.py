"""Template helper utilities."""
import humanize
import pendulum


def format_relative_time(dt):
    """Return a human-friendly relative time string (e.g. "3 hours ago")."""
    localized = pendulum.instance(dt, tz=pendulum.local_timezone())
    delta = pendulum.now() - localized
    return humanize.naturaldelta(delta)
