from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils import timezone
from apps.routes.models import Route
from apps.routes.serializers import RouteSerializer
from apps.pickups.models import Pickup
from apps.pickups.serializers import PickupSerializer
from drf_spectacular.utils import extend_schema

class RouteViewSet(viewsets.ModelViewSet):
    queryset = Route.objects.all()
    serializer_class = RouteSerializer
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(tags=['Resident'])
    @action(detail=False, methods=['get'])
    def ward_live(self, request):
        """
        Retrieves the active collection routes CITY-WIDE for today. 
        Allowing residents to see all cleanup vehicles moving through the city.
        """
        today = timezone.now().date()
        # Show ALL active trucks for today across the entire city
        routes = Route.objects.filter(route_date=today).select_related('ward', 'hks_worker')
        
        # Serialize with geo-features
        serializer = self.get_serializer(routes, many=True)
        return Response({
            "city_wide": True,
            "date": today.isoformat(),
            "total_active_trucks": routes.count(),
            "routes": serializer.data
        })

class TodayRouteView(APIView):
    """
    Retrieves the route and ordered pickups for the authenticated HKS Worker for today.
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(responses={200: {}})
    def get(self, request):
        if getattr(request.user, 'role', '') != 'HKS_WORKER':
            return Response({"error": "Only HKS Workers can access this endpoint"}, status=status.HTTP_403_FORBIDDEN)
            
        today = timezone.now().date()
        route = Route.objects.filter(hks_worker=request.user, route_date=today).first()
        
        if not route:
            return Response({"message": "No route assigned for today"}, status=status.HTTP_404_NOT_FOUND)
            
        pickups = Pickup.objects.filter(
            ward=route.ward, 
            scheduled_date=today,
            status__in=['pending', 'accepted']
        ).order_by('-is_instant', 'time_slot')
        
        return Response({
            "route": RouteSerializer(route).data,
            "pickups": PickupSerializer(pickups, many=True).data
        })
