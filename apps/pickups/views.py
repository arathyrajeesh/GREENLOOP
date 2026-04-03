from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count
from drf_spectacular.utils import extend_schema
from django.utils import timezone
from datetime import timedelta
from apps.pickups.models import Pickup, PickupVerification, PickupSlot
from apps.pickups.serializers import PickupSerializer, PickupSlotSerializer
from apps.pickups.serializers_verification import PickupVerificationSerializer

@extend_schema(tags=['Resident', 'HKS Worker'])
class PickupViewSet(viewsets.ModelViewSet):
    serializer_class = PickupSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if getattr(user, 'role', '') == 'RESIDENT':
            return Pickup.objects.select_related('resident', 'ward').filter(resident=user).order_by('-created_at')[:20]
        elif getattr(user, 'role', '') == 'HKS_WORKER':
            if user.ward:
                return Pickup.objects.select_related('resident', 'ward').filter(ward=user.ward).order_by('-created_at')[:20]
            return Pickup.objects.none()
        elif getattr(user, 'role', '') == 'ADMIN':
            ward_id = self.request.query_params.get('ward_id')
            queryset = Pickup.objects.select_related('resident', 'ward')
            if ward_id:
                return queryset.filter(ward_id=ward_id)
            return queryset.all()
        return Pickup.objects.none()

    @extend_schema(tags=['Resident'])
    @action(detail=False, methods=['get'])
    def availability(self, request):
        """
        Returns availability for each time slot for a given ward and date.
        Example: /api/v1/pickups/availability/?ward_id=1&date=2026-03-31
        """
        ward_id = request.query_params.get('ward_id')
        user = request.user
        
        # Fallback to user's ward if not provided in query params
        if not ward_id and hasattr(user, 'ward') and user.ward:
            ward_id = user.ward.id
            
        date_str = request.query_params.get('date', timezone.now().date().isoformat())
        
        if not ward_id:
            # Return Map with 'error' field instead of just an empty list. 
            # Providing an empty 'data' list as well so the frontend doesn't crash on list-expectations.
            return Response({
                "error": "Ward ID is missing. Please ensure your profile has a ward assigned.", 
                "slots": []
            }, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            from datetime import datetime
            scheduled_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return Response({
                "error": f"Invalid date format: {date_str}. Expected YYYY-MM-DD", 
                "slots": []
            }, status=status.HTTP_400_BAD_REQUEST)
            
        # Get active slots from database
        active_slots = PickupSlot.objects.filter(is_active=True)
        
        # Fallback: if no slots in DB, seed defaults for this request context
        if not active_slots.exists():
             defaults = [
                {"time_range": "08:00 - 10:00", "label": "Morning (8-10 AM)"},
                {"time_range": "10:00 - 12:00", "label": "Late Morning (10-12 PM)"},
                {"time_range": "14:00 - 16:00", "label": "Afternoon (2-4 PM)"},
                {"time_range": "16:00 - 18:00", "label": "Evening (4-6 PM)"},
             ]
             for d in defaults:
                  PickupSlot.objects.get_or_create(time_range=d['time_range'], defaults={'label': d['label']})
             active_slots = PickupSlot.objects.filter(is_active=True)

        # Get existing pickup counts for this date/ward
        pickup_counts = Pickup.objects.filter(
            ward_id=ward_id, 
            scheduled_date=scheduled_date
        ).values('time_slot_ref').annotate(count=Count('id'))
        
        counts_dict = {item['time_slot_ref']: item['count'] for item in pickup_counts}
        
        results = []
        for slot in active_slots:
            # Fallback values to ensure NO nulls ever reach Flutter
            # Crucially aligning 'time_range' and 'time_slot' to avoid type-cast errors on missing keys
            slot_id = str(slot.id) if slot.id else ""
            tr = str(slot.time_range or "00:00 - 00:00")
            lbl = str(slot.label or "Unknown Slot")
            cap = int(slot.capacity if slot.capacity is not None else 0)
            
            booked = int(counts_dict.get(slot.id, 0))
            remains = cap - booked
            
            results.append({
                "id": slot_id,
                "time_slot": tr,     # Legacy key
                "time_range": tr,    # Model/Serializer-aligned key
                "label": lbl,
                "capacity": cap,
                "booked_count": booked,
                "remaining_capacity": max(0, remains),
                "is_available": remains > 0 and slot.is_active is True
            })
            
        return Response(results)

    @extend_schema(tags=['Resident'])
    def perform_create(self, serializer):
        user = self.request.user
        save_kwargs = {}
        if getattr(user, 'role', '') == 'RESIDENT':
            save_kwargs['resident'] = user
            if user.ward and not serializer.validated_data.get('ward'):
                save_kwargs['ward'] = user.ward
        serializer.save(**save_kwargs)

    @extend_schema(tags=['Resident'])
    @extend_schema(tags=['HKS Worker'])
    def perform_update(self, serializer):
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
        contamination_flag = str(request.data.get('contamination_flag', 'False')).lower() == 'true'
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
                'contamination_flag': contamination_flag,
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
        
        # Celery Tasks are triggered in model save()
        from apps.pickups.tasks import flag_pickup_for_review
        
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

@extend_schema(tags=['Admin'])
class PickupSlotViewSet(viewsets.ModelViewSet):
    """
    Admin-only configuration for available pickup slots across the city.
    """
    queryset = PickupSlot.objects.all()
    serializer_class = PickupSlotSerializer
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAdminUser()]

@extend_schema(tags=['HKS Worker'])
class PickupVerificationViewSet(viewsets.GenericViewSet):
    queryset = PickupVerification.objects.all()
    serializer_class = PickupVerificationSerializer
    permission_classes = [permissions.IsAuthenticated]
