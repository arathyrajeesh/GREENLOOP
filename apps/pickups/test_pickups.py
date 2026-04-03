import pytest
from django.urls import reverse
from rest_framework import status
from django.contrib.gis.geos import Point
from apps.pickups.models import Pickup, PickupVerification

@pytest.mark.django_db
class TestPickupViewSet:
    def test_create_pickup_resident(self, authenticated_client, resident_user, ward):
        url = reverse('pickup-list')
        data = {
            "waste_type": "dry",
            "scheduled_date": "2026-04-01",
            "time_slot": "10:00-12:00",
            "location": {"type": "Point", "coordinates": [76.947, 8.525]}
        }
        response = authenticated_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert Pickup.objects.count() == 1
        pickup = Pickup.objects.first()
        assert pickup.resident == resident_user
        assert pickup.ward == resident_user.ward
        assert pickup.status == 'pending'
        assert response.data['booking_type'] == "Scheduled Slot"

    def test_create_instant_pickup_resident(self, authenticated_client, resident_user, ward):
        url = reverse('pickup-list')
        data = {
            "waste_type": "dry",
            "is_instant": True,
            "location": {"type": "Point", "coordinates": [76.947, 8.525]}
        }
        response = authenticated_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        pickup = Pickup.objects.get(id=response.data['id'])
        assert pickup.is_instant is True
        # Verify it was automatically accepted as per our new model logic
        assert pickup.status == 'accepted'
        assert response.data['booking_type'] == "Instant Booking"

    def test_cancel_pickup_too_late(self, authenticated_client, resident_user):
        from django.utils import timezone
        from datetime import timedelta
        from tests.factories import PickupFactory
        
        # Scheduled 1 hour from now
        future_dt = timezone.now() + timedelta(hours=1)
        pickup = PickupFactory(
            resident=resident_user, 
            scheduled_date=future_dt.date(),
            time_slot=future_dt.strftime("%H:%M") + "-12:00"
        )
        
        url = reverse('pickup-cancel', kwargs={'pk': pickup.pk})
        response = authenticated_client.patch(url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['error'] == "Too late to cancel"

    @pytest.mark.celery(CELERY_TASK_ALWAYS_EAGER=True)
    def test_complete_pickup_worker(self, worker_client, worker_user, resident_user):
        # Ensure worker and pickup are in same ward
        from tests.factories import PickupFactory
        pickup = PickupFactory(resident=resident_user, ward=worker_user.ward)
        
        url = reverse('pickup-complete', kwargs={'pk': pickup.pk})
        data = {
            "waste_photo_url": "http://example.com/photo.jpg",
            "ai_classification": "clean",
            "contamination_confidence": 0.9,
            "weight_kg": 10.5,
            "distance_meters": 50
        }
        response = worker_client.patch(url, data)
        assert response.status_code == status.HTTP_200_OK
        
        pickup.refresh_from_db()
        assert pickup.status == 'completed'
        assert PickupVerification.objects.filter(pickup=pickup).exists()

    def test_verify_scan_spatial(self, worker_client, worker_user, resident_user):
        # Ensure worker and pickup are in same ward
        from tests.factories import PickupFactory
        pickup = PickupFactory(resident=resident_user, ward=worker_user.ward)
        
        url = reverse('pickup-verify-scan', kwargs={'pk': pickup.pk})
        # Pickup location is [76.947, 8.525] (from factory)
        # 50m away
        worker_loc = {"type": "Point", "coordinates": [76.9474, 8.525]}
        data = {
            "qr_scan_data": pickup.qr_code or "dummy_qr",
            "worker_location": worker_loc
        }
        # Force a QR code for the test if it's missing
        if not pickup.qr_code:
            pickup.qr_code = "TEST_QR"
            pickup.save()
            data['qr_scan_data'] = "TEST_QR"
            
        response = worker_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['valid'] is True
        assert response.data['distance_meters'] < 100
