from rest_framework import viewsets, permissions
from apps.wards.models import Ward
from apps.wards.serializers import WardSerializer

class WardViewSet(viewsets.ModelViewSet):
    queryset = Ward.objects.all()
    serializer_class = WardSerializer
    permission_classes = [permissions.IsAuthenticated]
