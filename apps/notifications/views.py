from rest_framework import viewsets, permissions
from drf_spectacular.utils import extend_schema
from .models import Notification
from .serializers import NotificationSerializer

@extend_schema(tags=['Shared', 'Notifications'])
class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Notification.objects.none()
        
        user = self.request.user
        if not user or user.is_anonymous:
            return Notification.objects.none()
            
        return Notification.objects.filter(user=user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
