from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from apps.wards.models import Ward
from apps.wards.serializers import WardSerializer, WardAssignWorkersSerializer
from apps.users.serializers import UserSerializer
from apps.users.models import User

@extend_schema(tags=['Admin'])
class WardViewSet(viewsets.ModelViewSet):
    queryset = Ward.objects.all()
    serializer_class = WardSerializer
    
    def get_permissions(self):
        # Restrict most actions to admins. 
        # But allow authenticated users (workers/residents) to 'retrieve' a specific ward 
        # (e.g., they need to know details of their own ward).
        if self.action in ['list', 'create', 'update', 'partial_update', 'destroy', 'assign_workers', 'stats']:
            return [permissions.IsAdminUser()]
        return [permissions.IsAuthenticated()]

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Returns a non-GeoJSON summary of all wards for list views/tables."""
        wards = self.get_queryset()
        data = []
        for ward in wards:
            workers = ward.users.filter(role='HKS_WORKER')
            data.append({
                "id": ward.id,
                "name": ward.name,
                "number": ward.number,
                "worker_count": workers.count(),
                "resident_count": ward.users.filter(role='RESIDENT').count(),
                "worker_names": [w.name for w in workers],
                "point": {"lat": ward.location.y, "lng": ward.location.x}
            })
        return Response(data)

    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """Returns performance metrics for a specific ward."""
        ward = self.get_object()
        from apps.pickups.models import Pickup
        from django.db.models import Sum
        
        pickups = Pickup.objects.filter(ward=ward)
        completed = pickups.filter(status='completed').count()
        total_weight = pickups.filter(status='completed').aggregate(Sum('weight_kg'))['weight_kg__sum'] or 0.0
        
        return Response({
            "ward_name": ward.name,
            "total_pickups": pickups.count(),
            "completed_pickups": completed,
            "total_waste_kg": float(total_weight),
            "pending_complaints": ward.users.filter(role='RESIDENT', complaints__status='pending').count() # Simplified
        })

    @action(detail=True, methods=['get'])
    def workers(self, request, pk=None):
        """List all HKS workers currently assigned to this ward."""
        ward = self.get_object()
        workers = ward.users.filter(role='HKS_WORKER')
        serializer = UserSerializer(workers, many=True)
        return Response(serializer.data)

    @extend_schema(
        request=WardAssignWorkersSerializer,
        responses={200: {"status": "success message"}},
        description="Batch assign/unassign HKS workers to this ward."
    )
    @action(detail=True, methods=['post'])
    def assign_workers(self, request, pk=None):
        """Batch assign/unassign HKS workers to this ward."""
        ward = self.get_object()
        worker_ids = request.data.get('worker_ids', [])
        
        # Validate that all IDs exist and are HKS_WORKERs
        workers = User.objects.filter(id__in=worker_ids, role='HKS_WORKER')
        actual_ids = [str(w.id) for w in workers]
        
        # Check if any provided ID is missing or invalid
        if len(workers) != len(worker_ids):
            missing = set(worker_ids) - set(actual_ids)
            return Response(
                {"error": f"Invalid or non-worker IDs: {list(missing)}"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update ward for the selected workers
        workers.update(ward=ward)
        
        # Unassign workers currently in this ward who are NOT in the new list
        ward.users.filter(role='HKS_WORKER').exclude(id__in=worker_ids).update(ward=None)
        
        return Response({"status": f"Successfully assigned {len(worker_ids)} workers to ward {ward.name}"})
