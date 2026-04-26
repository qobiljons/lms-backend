from urllib.parse import parse_qs

from channels.auth import AuthMiddlewareStack
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import AccessToken

from apps.users.models import User

@database_sync_to_async
def _get_user(user_id):
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return AnonymousUser()

class JWTQueryAuthMiddleware:
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        token = None
        query_string = scope.get("query_string", b"").decode()
        query_params = parse_qs(query_string)
        if "token" in query_params:
            token = query_params["token"][0]

        if not token:
            headers = dict(scope.get("headers", []))
            auth_header = headers.get(b"authorization", b"").decode()
            if auth_header.lower().startswith("bearer "):
                token = auth_header.split(" ", 1)[1]

        if token:
            try:
                access_token = AccessToken(token)
                scope["user"] = await _get_user(access_token["user_id"])
            except (InvalidToken, TokenError, KeyError):
                scope["user"] = AnonymousUser()

        return await self.inner(scope, receive, send)

def JWTAuthMiddlewareStack(inner):
    return JWTQueryAuthMiddleware(AuthMiddlewareStack(inner))
