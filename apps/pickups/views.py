from rest_framework import viewsets, permissions
from apps.pickups.models import Pickup, PickupVerification
from apps.pickups.serializers import PickupSerializer
from apps.pickups.serializers_verification import PickupVerificationSerializer

class PickupViewSet(viewsets.ModelViewSet):
    queryset = Pickup.objects.all()
    serializer_class = PickupSerializer
    permission_classes = [permissions.IsAuthenticated]

class PickupVerificationViewSet(viewsets.ModelViewSet):
    queryset = PickupVerification.objects.all()
    serializer_class = PickupVerificationSerializer
    permission_classes = [permissions.IsAuthenticated]
