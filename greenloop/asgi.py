import os
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from channels.auth import AuthMiddlewareStack
import greenloop.routing

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "greenloop.settings.development"
)

django_asgi_app = get_asgi_application()

# Import middleware after django.setup() (called by get_asgi_application)
from greenloop.middleware import JWTAuthMiddleware

application = ProtocolTypeRouter({
    "http": django_asgi_app,

    "websocket": JWTAuthMiddleware(
        URLRouter(
            greenloop.routing.websocket_urlpatterns
        )
    ),
})
