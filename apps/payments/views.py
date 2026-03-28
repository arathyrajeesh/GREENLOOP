from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Sum, Count
from drf_spectacular.utils import extend_schema
from .models import FeeCollection
from .serializers import FeeCollectionSerializer

@extend_schema(tags=['Resident', 'HKS Worker', 'Admin'])
class FeeCollectionViewSet(viewsets.ModelViewSet):
    serializer_class = FeeCollectionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return FeeCollection.objects.none()
            
        user = self.request.user
        if not user or user.is_anonymous:
            return FeeCollection.objects.none()
            
        if user.role == 'RESIDENT':
            return FeeCollection.objects.filter(resident=user)
        return FeeCollection.objects.all()

    @extend_schema(tags=['HKS Worker'])
    def perform_create(self, serializer):
        serializer.save(collected_by=self.request.user)

    @extend_schema(tags=['HKS Worker'])
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """
        Daily summary of fee collections for the authenticated worker.
        """
        user = request.user
        if getattr(user, 'role', '') != 'HKS_WORKER':
            return Response({"error": "Only HKS Workers can access this summary"}, status=status.HTTP_403_FORBIDDEN)
            
        today = timezone.now().date()
        collections = FeeCollection.objects.filter(collected_by=user, payment_date__date=today)
        
        total_collected = collections.aggregate(total=Sum('amount'))['total'] or 0
        household_count = collections.values('resident').distinct().count()
        
        # Payment mode breakdown
        modes = collections.values('payment_method').annotate(count=Count('id'), total=Sum('amount'))
        mode_breakdown = {m['payment_method']: {"count": m['count'], "total": m['total']} for m in modes}
        
        return Response({
            "date": str(today),
            "total_collected": total_collected,
            "household_count": household_count,
            "payment_mode_breakdown": mode_breakdown
        }, status=status.HTTP_200_OK)
