from django.db import transaction
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from .models import SyncQueue
from .serializers import SyncQueueSerializer, DashboardStatsSerializer
from apps.routes.models import Route
from apps.routes.serializers import RouteSerializer
from apps.pickups.models import Pickup
from apps.pickups.serializers import PickupSerializer
from apps.wards.models import Ward
from apps.wards.serializers import WardSerializer
from django.core.cache import cache

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
    def upload(self, request):
        """
        Processes batched offline mutations chronologically with conflict detection.
        Expects a list of sync items with client_id and client_timestamp.
        """
        items = request.data
        if not isinstance(items, list):
            return Response({"error": "Expected a list of sync items."}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Sort by client_timestamp for chronological processing
        # Ensure we have a valid timestamp; fall back to a very old one if missing
        def get_timestamp(item):
            ts = item.get('client_timestamp')
            return ts if ts else "1970-01-01T00:00:00Z"
        
        items.sort(key=get_timestamp)

        results = []
        
        with transaction.atomic():
            for item in items:
                client_id = item.get('client_id')
                model_name = item.get('model_name')
                object_id = item.get('object_id')
                action_type = item.get('action')
                payload = item.get('payload', {})
                client_timestamp = item.get('client_timestamp')

                # 2. Idempotency Check
                if client_id:
                    existing = SyncQueue.objects.filter(user=request.user, client_id=client_id).first()
                    if existing:
                        results.append({
                            "client_id": str(client_id),
                            "status": existing.status,
                            "synced_at": existing.synced_at,
                            "message": "Already processed"
                        })
                        continue

                # 3. Create SyncQueue record
                sync_item = SyncQueue.objects.create(
                    user=request.user,
                    client_id=client_id,
                    client_timestamp=client_timestamp,
                    model_name=model_name,
                    object_id=object_id,
                    action=action_type,
                    payload=payload,
                    status="PENDING"
                )

                # 4. Process Logic (specifically for Pickups as per requirements)
                sync_status = "SYNCED"
                conflict_reason = None
                
                if model_name == "Pickup":
                    try:
                        pickup = Pickup.objects.get(id=object_id)
                        
                        # CONFLICT DETECTION
                        if action_type == "UPDATE":
                            new_status = payload.get('status')
                            if new_status == 'completed' and pickup.status == 'cancelled':
                                sync_status = "CONFLICT"
                                conflict_reason = "Pickup was admin-cancelled while worker was offline."
                            else:
                                # Apply the update safely
                                for key, value in payload.items():
                                    if hasattr(pickup, key):
                                        setattr(pickup, key, value)
                                pickup.save()
                    except Pickup.DoesNotExist:
                        sync_status = "ERROR"
                        conflict_reason = f"Pickup {object_id} not found on server."
                
                # Update sync item status
                sync_item.status = sync_status
                sync_item.conflict_reason = conflict_reason
                sync_item.is_synced = (sync_status == "SYNCED")
                if sync_item.is_synced:
                    sync_item.synced_at = timezone.now()
                sync_item.save()

                results.append({
                    "client_id": str(client_id) if client_id else None,
                    "status": sync_status,
                    "conflict_reason": conflict_reason,
                    "id": sync_item.id
                })

        return Response({
            "status": "completed",
            "items": results
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def active_locations(self, request):
        """
        Returns latest GPS positions for all active workers from Redis.
        Admin-only endpoint for live map fallback.
        """
        if request.user.role != 'ADMIN':
            return Response({"error": "Admin access required."}, status=status.HTTP_403_FORBIDDEN)

        active_worker_ids = cache.get("active_workers", set())
        if not isinstance(active_worker_ids, set):
            active_worker_ids = set()

        locations = []
        for worker_id in active_worker_ids:
            pos = cache.get(f"worker_pos:{worker_id}")
            if pos:
                locations.append(pos)
        
        return Response({
            "count": len(locations),
            "locations": locations
        })


class DashboardStatsViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DashboardStatsSerializer

    @extend_schema(tags=['Admin', 'Dashboard'])
    def list(self, request):
        range_val = request.query_params.get('range', '7d')
        today = timezone.now().date()
        
        # 1. KPIs
        pickups_today = Pickup.objects.filter(scheduled_date=today).count()
        # active workers = with role HKS_WORKER and recently updated or in cache
        active_workers_count = cache.get("active_workers_count", 0)
        if not active_workers_count:
             from apps.users.models import User
             active_workers_count = User.objects.filter(role='HKS_WORKER', is_active=True).count()
        
        from apps.complaints.models import Complaint
        pending_complaints = Complaint.objects.exclude(status__in=['resolved', 'closed']).count()
        
        total_waste = Pickup.objects.filter(status='completed').aggregate(models.Sum('weight_kg'))['weight_kg__sum'] or 0.0

        # 2. Weekly Trend (last 7 days)
        weekly_trend = []
        for i in range(6, -1, -1):
            date = today - timezone.timedelta(days=i)
            count = Pickup.objects.filter(scheduled_date=date, status='completed').count()
            weekly_trend.append({
                "date": date.strftime("%Y-%m-%d"),
                "count": count
            })

        # 3. Ward Comparison
        ward_comparison = []
        wards = Ward.objects.all()
        for ward in wards:
            p_count = Pickup.objects.filter(ward=ward, status='completed').count()
            c_count = Complaint.objects.filter(reporter__ward=ward).count()
            w_weight = Pickup.objects.filter(ward=ward, status='completed').aggregate(models.Sum('weight_kg'))['weight_kg__sum'] or 0.0
            
            ward_comparison.append({
                "ward_name": ward.name,
                "pickups": p_count,
                "complaints": c_count,
                "waste_weight": float(w_weight)
            })

        # 4. NPS Stats (Simplified placeholder)
        nps_stats = {
            "score": 75.0,
            "total_responses": 120,
            "recent_feedback": [
                {"rating": 5, "comment": "Excellent service!", "date": "2026-03-30"},
                {"rating": 4, "comment": "Very punctual.", "date": "2026-03-29"},
            ]
        }

        return Response({
            "kpis": {
                "pickups_today": pickups_today,
                "active_workers": active_workers_count,
                "pending_complaints": pending_complaints,
                "total_waste_kg": float(total_waste),
            },
            "weekly_trend": weekly_trend,
            "ward_comparison": ward_comparison,
            "nps_stats": nps_stats
        })
