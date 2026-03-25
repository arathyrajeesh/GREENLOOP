from rest_framework import viewsets, permissions
from apps.pickups.models import Pickup
from apps.pickups.serializers import PickupSerializer

class PickupViewSet(viewsets.ModelViewSet):
    queryset = Pickup.objects.all()
    serializer_class = PickupSerializer
    permission_classes = [permissions.IsAuthenticated]
