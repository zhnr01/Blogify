"""Business logic for comments."""
from __future__ import annotations

from .. import db
from ..models import Comment, Post


def get_comment(comment_id: int) -> Comment | None:
    return db.session.get(Comment, comment_id)


def list_comments_for_post(post: Post, page: int, per_page: int):
    """Return a pagination object of a post's comments, oldest first."""
    return (
        post.comments.order_by(Comment.timestamp.asc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )


def list_all_comments(page: int, per_page: int):
    """Return a pagination object of all comments, newest first (moderation)."""
    return (
        Comment.query.order_by(Comment.timestamp.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )


def create_comment(*, body: str, post: Post, author) -> Comment:
    comment = Comment(body=body, post=post, author=author)
    db.session.add(comment)
    db.session.commit()
    return comment


def set_disabled(comment: Comment, disabled: bool) -> Comment:
    comment.disabled = disabled
    db.session.add(comment)
    db.session.commit()
    return comment


def delete_comment(comment: Comment) -> None:
    db.session.delete(comment)
    db.session.commit()
