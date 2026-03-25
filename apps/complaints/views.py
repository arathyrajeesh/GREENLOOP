from rest_framework import viewsets, permissions
from .models import Complaint
from .serializers import ComplaintSerializer

class ComplaintViewSet(viewsets.ModelViewSet):
    serializer_class = ComplaintSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Complaint.objects.none()
        
        user = self.request.user
        if not user or user.is_anonymous:
            return Complaint.objects.none()
            
        if user.role == 'RESIDENT':
            return Complaint.objects.filter(resident=user)
        return Complaint.objects.all()
