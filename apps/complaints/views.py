from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from django.db import models
from django.utils import timezone
from .models import Complaint
from .serializers import ComplaintSerializer, ComplaintHeatmapSerializer
from apps.notifications.tasks import notify_admin_new_complaint

@extend_schema(tags=['Resident', 'HKS Worker', 'Admin'])
class ComplaintViewSet(viewsets.ModelViewSet):
    serializer_class = ComplaintSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Complaint.objects.none()
        
        user = self.request.user
        if not user or user.is_anonymous:
            return Complaint.objects.none()
            
        if user.role in ['ADMIN', 'HKS_WORKER']:
            if user.role == 'ADMIN':
                queryset = Complaint.objects.select_related('reporter', 'assigned_to').all()
            else:
                # Workers see assigned or reported
                queryset = Complaint.objects.select_related('reporter', 'assigned_to').filter(models.Q(assigned_to=user) | models.Q(reporter=user))
        else:
            # Residents see their own
            queryset = Complaint.objects.select_related('reporter', 'assigned_to').filter(reporter=user)
            
        # Acceptance Criteria: sorted by priority (Highest=4 first) and age (Oldest=ASC first)
        return queryset.order_by('-priority', 'created_at')

    @extend_schema(tags=['Resident'])
    @action(detail=False, methods=['get'], url_path='get-upload-url')
    def get_upload_url(self, request):
        """
        Returns a placeholder S3-style response for the Flutter app.
        This fixes the "type 'Null' is not a subtype of type 'String'" error by 
        ensuring no expected keys are missing or null in Dart.
        """
        return Response({
            "upload_url": "/api/v1/complaints/", 
            "method": "POST",
            "field": "image",
            "s3_key": f"complaints/{request.user.id}_placeholder.jpg",
            "bucket": "greenloop-storage",
            "url": "/api/v1/complaints/", # Alias for upload_url
            "message": "Direct upload to the complaint endpoint is enabled."
        })

    @extend_schema(tags=['Resident'])
    def perform_create(self, serializer):
        complaint = serializer.save(reporter=self.request.user, status='submitted')
        try:
            notify_admin_new_complaint.delay(complaint.id)
        except Exception as e:
            # Prevent 500 error if Redis/Celery is down. 
            # The complaint is still saved successfully.
            print(f"ALARM: Notification failed to queue: {e}")

    @extend_schema(tags=['Admin'])
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def assign(self, request, pk=None):
        """Allows admins to assign a complaint to a worker."""
        complaint = self.get_object()
        worker_id = request.data.get('worker_id')
        if not worker_id:
            return Response({"error": "worker_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        from apps.users.models import User
        try:
            worker = User.objects.get(id=worker_id, role__in=['ADMIN', 'HKS_WORKER'])
        except User.DoesNotExist:
            return Response({"error": "Invalid or non-assignable worker ID"}, status=status.HTTP_400_BAD_REQUEST)
            
        complaint.assigned_to = worker
        complaint.status = 'assigned'
        complaint.save()
        return Response(ComplaintSerializer(complaint).data)

    @extend_schema(tags=['HKS Worker'])
    @action(detail=True, methods=['post'])
    def advance_status(self, request, pk=None):
        """Advances the complaint through its lifecycle."""
        complaint = self.get_object()
        transitions = {
            'submitted': 'assigned',
            'assigned': 'in-progress',
            'in-progress': 'resolved',
            'resolved': 'closed'
        }
        
        # Security: Residents can't advance statuses past submitted? 
        # Usually workers/admins do this.
        if self.request.user.role == 'RESIDENT':
             return Response({"error": "Residents cannot advance complaint status"}, status=status.HTTP_403_FORBIDDEN)

        current_status = complaint.status
        next_status = transitions.get(current_status)
        
        if not next_status:
            return Response({"error": f"Cannot advance status from {current_status}"}, status=status.HTTP_400_BAD_REQUEST)
            
        complaint.status = next_status
        if next_status == 'resolved':
            complaint.resolved_at = timezone.now()
        complaint.save()
        return Response(ComplaintSerializer(complaint).data)

    @extend_schema(tags=['Admin', 'Heatmap'])
    @action(detail=False, methods=['get'])
    def heatmap(self, request):
        """Identifies complaint hotspots using PostGIS KMeans clustering."""
        k = int(request.query_params.get('k', 5))
        
        from django.db import connection
        with connection.cursor() as cursor:
            # Spatial clustering query
            query = """
                SELECT 
                    cluster_id, 
                    count(*) as point_count, 
                    ST_X(ST_Centroid(ST_Collect(location::geometry))) as longitude,
                    ST_Y(ST_Centroid(ST_Collect(location::geometry))) as latitude
                FROM (
                    SELECT 
                        ST_ClusterKMeans(location::geometry, %s) OVER() as cluster_id,
                        location
                    FROM complaints_complaint
                    WHERE location IS NOT NULL
                ) sub
                GROUP BY cluster_id
            """
            cursor.execute(query, [k])
            rows = cursor.fetchall()
            
        data = [
            {"cluster_id": r[0], "point_count": r[1], "longitude": r[2], "latitude": r[3]}
            for r in rows
        ]
        return Response(data)
