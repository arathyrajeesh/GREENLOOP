from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.wards.models import Ward
from apps.wards.serializers import WardSerializer
from apps.users.serializers import UserSerializer
from apps.users.models import User

class WardViewSet(viewsets.ModelViewSet):
    queryset = Ward.objects.all()
    serializer_class = WardSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'assign_workers']:
            # Allow IsAdminUser for management tasks
            return [permissions.IsAdminUser()]
        return [permissions.IsAuthenticated()]

    @action(detail=True, methods=['get'])
    def workers(self, request, pk=None):
        """List all HKS workers currently assigned to this ward."""
        ward = self.get_object()
        workers = ward.users.filter(role='HKS_WORKER')
        serializer = UserSerializer(workers, many=True)
        return Response(serializer.data)

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
