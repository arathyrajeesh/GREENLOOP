from django.urls import re_path
from apps.notifications.consumers import NotificationConsumer
from apps.dashboard.consumers import TrackingConsumer

websocket_urlpatterns = [
    re_path(r"ws/notifications/$", NotificationConsumer.as_asgi()),
    re_path(r"ws/tracking/$", TrackingConsumer.as_asgi()),
]
