from rest_framework import viewsets, permissions
from apps.routes.models import Route
from apps.routes.serializers import RouteSerializer

class RouteViewSet(viewsets.ModelViewSet):
    queryset = Route.objects.all()
    serializer_class = RouteSerializer
    permission_classes = [permissions.IsAuthenticated]
