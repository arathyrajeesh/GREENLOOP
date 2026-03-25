from rest_framework import viewsets, permissions
from .models import FeeCollection
from .serializers import FeeCollectionSerializer

class FeeCollectionViewSet(viewsets.ModelViewSet):
    serializer_class = FeeCollectionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return FeeCollection.objects.none()
            
        user = self.request.user
        if not user or user.is_anonymous:
            return FeeCollection.objects.none()
            
        if user.role == 'RESIDENT':
            return FeeCollection.objects.filter(resident=user)
        return FeeCollection.objects.all()
