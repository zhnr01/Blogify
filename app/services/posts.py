"""Business logic for posts."""
from __future__ import annotations

from .. import cache, db
from ..models import Post

# Cache key/namespace for the paginated post feed. Bumping the version on write
# invalidates every cached page at once (see ``invalidate_feed``).
_FEED_NAMESPACE = "posts:feed"


def get_post(post_id: int) -> Post | None:
    """Return a post by id, or None."""
    return db.session.get(Post, post_id)


def list_posts(page: int, per_page: int):
    """Return a pagination object of posts, newest first."""
    return (
        Post.query.order_by(Post.timestamp.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )


def create_post(*, title: str | None, body: str, author) -> Post:
    """Create and persist a post, then invalidate the cached feed."""
    post = Post(title=title, body=body, author=author)
    db.session.add(post)
    db.session.commit()
    invalidate_feed()
    return post


def update_post(post: Post, *, title: str | None = None, body: str | None = None) -> Post:
    """Update a post in place and persist the change."""
    if title is not None:
        post.title = title
    if body is not None:
        post.body = body
    db.session.add(post)
    db.session.commit()
    invalidate_feed()
    return post


def invalidate_feed() -> None:
    """Drop cached feed pages after a write. Safe when caching is disabled."""
    try:
        version = cache.get(f"{_FEED_NAMESPACE}:version") or 0
        cache.set(f"{_FEED_NAMESPACE}:version", version + 1)
    except Exception:
        # Never let a cache backend failure break a write path.
        pass


def feed_version() -> int:
    """Current feed cache version, used to build versioned cache keys."""
    try:
        return cache.get(f"{_FEED_NAMESPACE}:version") or 0
    except Exception:
        return 0
