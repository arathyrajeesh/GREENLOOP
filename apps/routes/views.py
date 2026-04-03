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
        Retrieves the active collection routes in the resident's ward for today.
        Allows residents to see where the truck is for 'Instant Pickup' planning.
        """
        user = request.user
        if not hasattr(user, 'ward') or not user.ward:
             return Response({
                 "error": "No ward assigned to your profile. Please update your profile."
             }, status=status.HTTP_400_BAD_REQUEST)

        today = timezone.now().date()
        routes = Route.objects.filter(ward=user.ward, route_date=today)
        
        # Serialize with geo-features
        serializer = self.get_serializer(routes, many=True)
        return Response({
            "ward_name": user.ward.name,
            "date": today.isoformat(),
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
