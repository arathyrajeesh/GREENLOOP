from rest_framework import viewsets, permissions, views, response, status
from drf_spectacular.utils import extend_schema
from .models import Notification
from .serializers import NotificationSerializer
from .utils import send_push_notification

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

@extend_schema(tags=['Admin', 'Debug'])
class TestPushNotificationView(views.APIView):
    """
    Example view to test push notifications.
    Expected payload: {"title": "Hello", "body": "This is a test notification"}
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        title = request.data.get('title', 'Test Notification')
        body = request.data.get('body', 'This is a test notification from the Firebase v1 API.')
        
        user = request.user
        if not user.fcm_token:
            return response.Response(
                {"error": "User does not have an FCM token registered."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        message_id = send_push_notification(user, title, body, data={"test": "true"})
        
        if message_id:
            return response.Response({
                "message": "Notification sent successfully!",
                "firebase_message_id": message_id
            })
        else:
            return response.Response({
                "error": "Failed to send notification. Check logs for details."
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
