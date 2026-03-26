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

    @action(detail=True, methods=['post'])
    def verify_scan(self, request, pk=None):
        pickup = self.get_object()
        user = request.user
        
        if getattr(user, 'role', '') != 'HKS_WORKER':
             return Response({"error": "Only HKS Workers can verify pickups"}, status=status.HTTP_403_FORBIDDEN)
             
        if user.ward != pickup.ward:
             return Response({"error": "You are not assigned to this pickup's ward"}, status=status.HTTP_403_FORBIDDEN)

        qr_data = request.data.get('qr_scan_data', '')
        is_manual_entry = str(request.data.get('is_manual_entry', 'False')).lower() == 'true'
        
        if not is_manual_entry and qr_data != pickup.qr_code:
            return Response({"error": "Invalid QR Code for this pickup"}, status=status.HTTP_400_BAD_REQUEST)
                
        loc_data = request.data.get('worker_location')
        if not loc_data or 'coordinates' not in loc_data:
            return Response({"error": "worker_location (GeoJSON Point format) is required"}, status=status.HTTP_400_BAD_REQUEST)
            
        coords = loc_data['coordinates']
        try:
            from django.contrib.gis.geos import Point
            worker_pt = Point(coords[0], coords[1], srid=4326)
            
            # PostGIS ST_Distance calculation (~meters via Mercator transform)
            pickup_pt = pickup.location.clone()
            pickup_pt.srid = 4326
                
            pickup_pt.transform(3857)
            worker_pt.transform(3857)
            distance_m = pickup_pt.distance(worker_pt)
            
            if distance_m > 100:
                return Response({
                    "valid": False, 
                    "requires_override": True, 
                    "distance_meters": round(distance_m, 2),
                    "error": "Location is beyond 100m from pickup point"
                }, status=status.HTTP_400_BAD_REQUEST)
                
            return Response({
                "valid": True,
                "distance_meters": round(distance_m, 2)
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({"error": f"Invalid coordinates: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['patch'])
    def complete(self, request, pk=None):
        pickup = self.get_object()
        user = request.user
        
        if getattr(user, 'role', '') != 'HKS_WORKER':
             return Response({"error": "Only HKS Workers can complete pickups"}, status=status.HTTP_403_FORBIDDEN)
             
        waste_photo_url = request.data.get('waste_photo_url')
        ai_classification = request.data.get('ai_classification', '')
        contamination_confidence = request.data.get('contamination_confidence')
        weight_kg = request.data.get('weight_kg')
        override_notes = request.data.get('notes', '')
        is_gps_override = str(request.data.get('is_gps_override', 'False')).lower() == 'true'
        distance_meters = request.data.get('distance_meters')
        
        if is_gps_override and not override_notes:
            return Response({"error": "Mandatory notes required for GPS override"}, status=status.HTTP_400_BAD_REQUEST)
            
        requires_admin_review = False
        parsed_conf = None
        if contamination_confidence is not None:
            try:
                parsed_conf = float(contamination_confidence)
                if parsed_conf < 0.70:
                    requires_admin_review = True
            except ValueError:
                pass
                
        verification, created = PickupVerification.objects.update_or_create(
            pickup=pickup,
            defaults={
                'verified_by': user,
                'waste_photo_url': waste_photo_url,
                'ai_classification': ai_classification,
                'contamination_confidence': parsed_conf,
                'requires_admin_review': requires_admin_review,
                'distance_meters': float(distance_meters) if distance_meters else None,
                'is_gps_override': is_gps_override,
            }
        )
        
        pickup.status = 'completed'
        if override_notes:
            pickup.notes = override_notes
        if weight_kg is not None:
            try:
                pickup.weight_kg = float(weight_kg)
            except ValueError:
                pass
                
        pickup.save()  # completed_at is set in model's save() method
        
        # Trigger Celery Tasks asynchronously
        from apps.rewards.tasks import award_greenleaf_points
        from apps.notifications.tasks import notify_resident_pickup_complete
        from apps.pickups.tasks import flag_pickup_for_review
        
        award_greenleaf_points.delay(pickup.id)
        notify_resident_pickup_complete.delay(pickup.id)
        
        if requires_admin_review:
            flag_pickup_for_review.delay(pickup.id)
            
        # Check weight threshold for payment requirement
        payment_required = False
        if weight_kg and float(weight_kg) > 50:
            payment_required = True
            
        return Response({
            "status": "completed", 
            "payment_required": payment_required,
            "message": "Fee collection required for weight > 50kg" if payment_required else "Pickup completed"
        })

class PickupVerificationViewSet(viewsets.ModelViewSet):
    queryset = PickupVerification.objects.all()
    serializer_class = PickupVerificationSerializer
    permission_classes = [permissions.IsAuthenticated]
