from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from .models import SyncQueue
from .serializers import SyncQueueSerializer
from apps.routes.models import Route
from apps.routes.serializers import RouteSerializer
from apps.pickups.models import Pickup
from apps.pickups.serializers import PickupSerializer
from apps.wards.models import Ward
from apps.wards.serializers import WardSerializer

class SyncQueueViewSet(viewsets.ModelViewSet):
    queryset = SyncQueue.objects.all()
    serializer_class = SyncQueueSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return SyncQueue.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'])
    def prefetch(self, request):
        """
        Returns all data required for the HKS worker's today's route.
        Includes: Route, Pickups, and Ward data.
        """
        user = request.user
        if user.role != 'HKS_WORKER':
            return Response({"error": "Only HKS workers can prefetch route data."}, status=status.HTTP_403_FORBIDDEN)

        today = timezone.now().date()
        
        # 1. Get Today's Route
        route = Route.objects.filter(hks_worker=user, route_date=today).first()
        route_data = RouteSerializer(route).data if route else None

        # 2. Get Assigned Pickups (based on the worker's assigned routes/wards)
        # For simplicity, we get all pending/accepted pickups in the ward(s) assigned to them today.
        pickups = Pickup.objects.none()
        wards_data = []
        
        if route:
            pickups = Pickup.objects.filter(ward=route.ward, scheduled_date=today).exclude(status='cancelled')
            wards_data = [WardSerializer(route.ward).data]
        
        pickup_data = PickupSerializer(pickups, many=True).data

        return Response({
            "today": today,
            "route": route_data,
            "pickups": pickup_data,
            "wards": wards_data,
            "server_time": timezone.now()
        })

    @action(detail=False, methods=['post'])
    def push(self, request):
        """
        Bulk uploads local mutations into the SyncQueue.
        Expects a list of sync items.
        """
        items = request.data
        if not isinstance(items, list):
            return Response({"error": "Expected a list of sync items."}, status=status.HTTP_400_BAD_REQUEST)

        created_items = []
        for item in items:
            serializer = self.get_serializer(data=item)
            if serializer.is_valid():
                serializer.save(user=request.user)
                created_items.append(serializer.data)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "status": "success",
            "count": len(created_items),
            "items": created_items
        }, status=status.HTTP_201_CREATED)
