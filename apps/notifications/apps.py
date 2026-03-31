from django.apps import AppConfig
from .firebase import initialize_firebase

class NotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.notifications'

    def ready(self):
        initialize_firebase()