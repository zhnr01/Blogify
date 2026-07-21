"""Marshmallow schemas for API (de)serialization and input validation.

Schemas are the single source of truth for the shape of API payloads. Input is
validated here (raising a 422 via the error handler) rather than by hand in the
view functions.
"""
from marshmallow import Schema, fields, validate


class PostSchema(Schema):
    """Serialize a Post and validate incoming post payloads."""

    id = fields.Int(dump_only=True)
    url = fields.Url(dump_only=True)
    title = fields.Str(
        required=False,
        allow_none=True,
        validate=validate.Length(max=80),
    )
    body = fields.Str(
        required=True,
        validate=validate.Length(min=1, error="post body must not be empty"),
    )
    body_html = fields.Str(dump_only=True)
    timestamp = fields.DateTime(dump_only=True)
    author = fields.Str(attribute="author.username", dump_only=True)
    comment_count = fields.Method("get_comment_count", dump_only=True)

    def get_comment_count(self, obj):
        return obj.comments.count()


class UserSchema(Schema):
    """Public serialization of a user."""

    id = fields.Int(dump_only=True)
    username = fields.Str(dump_only=True)
    member_since = fields.DateTime(dump_only=True)
    last_seen = fields.DateTime(dump_only=True)
    post_count = fields.Method("get_post_count", dump_only=True)

    def get_post_count(self, obj):
        return obj.posts.count()


class CommentSchema(Schema):
    """Serialize a Comment and validate incoming comment payloads."""

    id = fields.Int(dump_only=True)
    body = fields.Str(
        required=True,
        validate=validate.Length(min=1, error="comment body must not be empty"),
    )
    body_html = fields.Str(dump_only=True)
    timestamp = fields.DateTime(dump_only=True)
    author = fields.Str(attribute="author.username", dump_only=True)
    disabled = fields.Bool(dump_only=True)


post_schema = PostSchema()
posts_schema = PostSchema(many=True)
user_schema = UserSchema()
users_schema = UserSchema(many=True)
comment_schema = CommentSchema()
comments_schema = CommentSchema(many=True)
