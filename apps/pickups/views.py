from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from datetime import timedelta
from apps.pickups.models import Pickup, PickupVerification
from apps.pickups.serializers import PickupSerializer
from apps.pickups.serializers_verification import PickupVerificationSerializer

class PickupViewSet(viewsets.ModelViewSet):
    serializer_class = PickupSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if getattr(user, 'role', '') == 'RESIDENT':
            return Pickup.objects.filter(resident=user)
        elif getattr(user, 'role', '') == 'HKS_WORKER':
            if user.ward:
                return Pickup.objects.filter(ward=user.ward)
            return Pickup.objects.none()
        elif getattr(user, 'role', '') == 'ADMIN':
            ward_id = self.request.query_params.get('ward_id')
            if ward_id:
                return Pickup.objects.filter(ward_id=ward_id)
            return Pickup.objects.all()
        return Pickup.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        save_kwargs = {}
        if getattr(user, 'role', '') == 'RESIDENT':
            save_kwargs['resident'] = user
            if user.ward and not serializer.validated_data.get('ward'):
                save_kwargs['ward'] = user.ward
        serializer.save(**save_kwargs)

    @action(detail=True, methods=['patch'])
    def cancel(self, request, pk=None):
        pickup = self.get_object()
        
        # Validation: Cannot cancel less than 2 hours before scheduled time
        now = timezone.now()
        scheduled = pickup.scheduled_datetime
        
        if scheduled and (scheduled - now) < timedelta(hours=2) and (scheduled > now):
            return Response(
                {"error": "Too late to cancel"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        pickup.status = 'cancelled'
        pickup.save()
        return Response({"status": "cancelled"})

    @action(detail=True, methods=['patch'])
    def complete(self, request, pk=None):
        pickup = self.get_object()
        pickup.status = 'completed'
        pickup.save()  # completed_at is set in model's save() method
        return Response({"status": "completed"})

class PickupVerificationViewSet(viewsets.ModelViewSet):
    queryset = PickupVerification.objects.all()
    serializer_class = PickupVerificationSerializer
    permission_classes = [permissions.IsAuthenticated]
