from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken
import urllib.parse

@database_sync_to_async
def get_user(token_key):
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        access_token = AccessToken(token_key)
        user_id = access_token.get('user_id')
        if not user_id:
            return AnonymousUser()
        return User.objects.get(id=user_id)
    except Exception:
        return AnonymousUser()

class JWTAuthMiddleware:
    """
    Custom middleware that takes a token from the query string and authenticates the user.
    Usage: ws://host/ws/path/?token=<jwt_token>
    """
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        # 1. Search in query string (?token=...)
        query_string = scope.get("query_string", b"").decode()
        query_params = urllib.parse.parse_qs(query_string)
        token = query_params.get("token", [None])[0]
        
        # 2. Fallback: Search in headers (Authorization: Bearer <token>)
        if not token:
            headers = dict(scope.get("headers", []))
            # Header keys are in bytes and lowercase in Channels
            auth_header = headers.get(b"authorization", b"").decode()
            if auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]

        if token:
            scope["user"] = await get_user(token)
        else:
            scope["user"] = AnonymousUser()
            
        return await self.app(scope, receive, send)
