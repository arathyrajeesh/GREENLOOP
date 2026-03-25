from rest_framework import viewsets, permissions
from .models import FeeCollection
from .serializers import FeeCollectionSerializer

class FeeCollectionViewSet(viewsets.ModelViewSet):
    serializer_class = FeeCollectionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'RESIDENT':
            return FeeCollection.objects.filter(resident=user)
        return FeeCollection.objects.all()
