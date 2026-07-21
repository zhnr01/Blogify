"""Unit tests for the service layer (posts and comments)."""
from app.services import comments as comment_service
from app.services import posts as post_service


def test_create_and_get_post(app, user):
    post = post_service.create_post(title='Hello', body='World body', author=user)
    assert post.id is not None
    assert post_service.get_post(post.id) is post


def test_update_post(app, user):
    post = post_service.create_post(title='Old', body='Old body', author=user)
    updated = post_service.update_post(post, title='New', body='New body')
    assert updated.title == 'New'
    assert updated.body == 'New body'


def test_list_posts_orders_newest_first(app, user):
    post_service.create_post(title='First', body='first', author=user)
    post_service.create_post(title='Second', body='second', author=user)
    pagination = post_service.list_posts(page=1, per_page=10)
    titles = [p.title for p in pagination.items]
    assert titles == ['Second', 'First']


def test_feed_reflects_writes(app, user):
    # With NullCache (testing default) every read is fresh; the feed must
    # always reflect the latest writes.
    post_service.create_post(title='One', body='one', author=user)
    _, total = post_service.list_feed_ids(page=1, per_page=10)
    assert total == 1
    post_service.create_post(title='Two', body='two', author=user)
    _, total2 = post_service.list_feed_ids(page=1, per_page=10)
    assert total2 == 2


def test_feed_cache_invalidation_bumps_version(app, user, monkeypatch):
    # Swap in a real (in-process) cache to exercise version-based invalidation.
    from cachelib import SimpleCache

    from app import cache
    store = SimpleCache()
    monkeypatch.setattr(cache, 'get', store.get)
    monkeypatch.setattr(cache, 'set', store.set)

    post_service.create_post(title='One', body='one', author=user)
    post_service.list_feed_ids(page=1, per_page=10)  # populate cache
    version_before = post_service.feed_version()
    post_service.create_post(title='Two', body='two', author=user)
    assert post_service.feed_version() == version_before + 1


def test_create_comment(app, user):
    post = post_service.create_post(title='P', body='body', author=user)
    comment = comment_service.create_comment(body='nice', post=post, author=user)
    assert comment.id is not None
    assert comment.post_id == post.id


def test_moderation_toggle(app, user):
    post = post_service.create_post(title='P', body='body', author=user)
    comment = comment_service.create_comment(body='x', post=post, author=user)
    comment_service.set_disabled(comment, True)
    assert comment.disabled is True
    comment_service.set_disabled(comment, False)
    assert comment.disabled is False
