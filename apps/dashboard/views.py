from rest_framework import viewsets, permissions
from .models import SyncQueue
from .serializers import SyncQueueSerializer

class SyncQueueViewSet(viewsets.ModelViewSet):
    queryset = SyncQueue.objects.all()
    serializer_class = SyncQueueSerializer
    permission_classes = [permissions.IsAuthenticated]
