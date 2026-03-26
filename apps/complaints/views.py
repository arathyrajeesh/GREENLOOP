from rest_framework import viewsets, permissions
from .models import Complaint
from .serializers import ComplaintSerializer
from apps.notifications.tasks import notify_admin_new_complaint

class ComplaintViewSet(viewsets.ModelViewSet):
    serializer_class = ComplaintSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Complaint.objects.none()
        
        user = self.request.user
        if not user or user.is_anonymous:
            return Complaint.objects.none()
            
        if user.role in ['RESIDENT', 'HKS_WORKER']:
            return Complaint.objects.filter(reporter=user)
        return Complaint.objects.all()

    def perform_create(self, serializer):
        complaint = serializer.save(reporter=self.request.user, status='PENDING')
        notify_admin_new_complaint.delay(complaint.id)
