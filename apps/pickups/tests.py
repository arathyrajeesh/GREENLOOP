from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch
from apps.users.models import User
from apps.wards.models import Ward
from apps.pickups.models import Pickup, PickupVerification

class PickupAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        
        # Create Ward
        self.ward = Ward.objects.create(
            name="Test Ward 1", 
            number=1,
            location="POINT(0.5 0.5)",
            boundary="POLYGON((0 0, 0 1, 1 1, 1 0, 0 0))"
        )
        self.ward2 = Ward.objects.create(
            name="Test Ward 2", 
            number=2,
            location="POINT(1.5 1.5)",
            boundary="POLYGON((1 1, 1 2, 2 2, 2 1, 1 1))"
        )
        
        # Create Users
        self.resident1 = User.objects.create(email="r1@test.com", name="R1", role="RESIDENT", ward=self.ward)
        self.resident1.set_password('testpass')
        self.resident1.save()
        
        self.resident2 = User.objects.create(email="r2@test.com", name="R2", role="RESIDENT", ward=self.ward2)
        
        self.worker = User.objects.create(email="w1@test.com", name="W1", role="HKS_WORKER", ward=self.ward)
        
        self.admin = User.objects.create(email="admin@test.com", name="Admin", role="ADMIN")
        
        # Create Pickups
        self.p1 = Pickup.objects.create(
            resident=self.resident1, ward=self.ward, waste_type="dry", 
            location="POINT(0.5 0.5)", scheduled_date=timezone.now().date(),
            time_slot="10:00-12:00"
        )
        self.p2 = Pickup.objects.create(
            resident=self.resident2, ward=self.ward2, waste_type="wet", 
            location="POINT(0.5 0.5)", scheduled_date=timezone.now().date(),
            time_slot="14:00-16:00"
        )
        
        self.list_url = reverse('pickup-list')
        
    def test_resident_pickup_creation(self):
        """Test resident can create pickup and it auto-assigns resident and ward"""
        self.client.force_authenticate(user=self.resident1)
        data = {
            "waste_type": "hazardous",
            "scheduled_date": timezone.now().date().isoformat(),
            "time_slot": "08:00-10:00",
            "location": {"type": "Point", "coordinates": [0.5, 0.5]}
        }
        response = self.client.post(self.list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify it was assigned to resident1 and ward1
        pickup_id = response.data['id']
        pickup = Pickup.objects.get(id=pickup_id)
        self.assertEqual(pickup.resident, self.resident1)
        self.assertEqual(pickup.ward, self.ward)
        self.assertIsNotNone(pickup.qr_code)
        
    def test_role_based_filtering(self):
        """Test RBAC for Pickup List"""
        # Resident 1 should only see p1
        self.client.force_authenticate(user=self.resident1)
        res = self.client.get(self.list_url)
        self.assertEqual(len(res.data['features']), 1)
        self.assertEqual(res.data['features'][0]['id'], str(self.p1.id))
        
        # Worker 1 (Ward 1) should only see p1
        self.client.force_authenticate(user=self.worker)
        res = self.client.get(self.list_url)
        self.assertEqual(len(res.data['features']), 1)
        self.assertEqual(res.data['features'][0]['id'], str(self.p1.id))
        
        # Admin should see both
        self.client.force_authenticate(user=self.admin)
        res = self.client.get(self.list_url)
        self.assertEqual(len(res.data['features']), 2)
        
        # Admin filtering by ward
        res = self.client.get(f"{self.list_url}?ward_id={self.ward2.id}")
        self.assertEqual(len(res.data['features']), 1)
        self.assertEqual(res.data['features'][0]['id'], str(self.p2.id))

    def test_cancellation_window(self):
        """Test cancelling less than 2 hours before scheduled time fails"""
        now = timezone.now()
        
        # Set p1 scheduled time to exactly 1 hour from now
        future_dt = now + timedelta(hours=1)
        self.p1.scheduled_date = future_dt.date()
        self.p1.time_slot = future_dt.strftime("%H:%M") + "-" + (future_dt + timedelta(hours=2)).strftime("%H:%M")
        self.p1.save()
        
        self.client.force_authenticate(user=self.resident1)
        cancel_url = reverse('pickup-cancel', args=[self.p1.id])
        res = self.client.patch(cancel_url)
        
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data['error'], "Too late to cancel")
        self.p1.refresh_from_db()
        self.assertEqual(self.p1.status, 'pending')
        
        # Set p1 scheduled time to 3 hours from now
        future_dt = now + timedelta(hours=3)
        self.p1.scheduled_date = future_dt.date()
        self.p1.time_slot = future_dt.strftime("%H:%M") + "-" + (future_dt + timedelta(hours=2)).strftime("%H:%M")
        self.p1.save()
        
        res = self.client.patch(cancel_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.p1.refresh_from_db()
        self.assertEqual(self.p1.status, 'cancelled')
        
    def test_complete_action(self):
        """Test custom complete action"""
        self.client.force_authenticate(user=self.worker)
        complete_url = reverse('pickup-complete', args=[self.p1.id])
        res = self.client.patch(complete_url)
        
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.p1.refresh_from_db()
        self.assertEqual(self.p1.status, 'completed')
        self.assertIsNotNone(self.p1.completed_at)

    def test_verify_scan_success(self):
        """Worker verifies QR securely within 100m."""
        self.client.force_authenticate(user=self.worker)
        # 1 degree is roughly 111km, so 0.0005 is roughly 55.5m (within 100m limit)
        url = reverse('pickup-verify-scan', kwargs={'pk': self.p1.id})
        data = {
            "qr_scan_data": self.p1.qr_code,
            "worker_location": {
                "type": "Point",
                "coordinates": [0.5005, 0.5]
            }
        }
        res = self.client.post(url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.data['valid'])
        self.assertTrue(res.data['distance_meters'] < 100)

    def test_verify_scan_gps_failure(self):
        """Worker verifies QR but is over 100m away, forcing a manual override flag."""
        self.client.force_authenticate(user=self.worker)
        # 0.002 degrees is roughly 222m (beyond 100m limit)
        url = reverse('pickup-verify-scan', kwargs={'pk': self.p1.id})
        data = {
            "qr_scan_data": self.p1.qr_code,
            "worker_location": {
                "type": "Point",
                "coordinates": [0.502, 0.5]
            }
        }
        res = self.client.post(url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(res.data['valid'])
        self.assertTrue(res.data['requires_override'])
        self.assertTrue(res.data['distance_meters'] > 100)

    @patch('apps.rewards.tasks.award_greenleaf_points.delay')
    @patch('apps.notifications.tasks.notify_resident_pickup_complete.delay')
    @patch('apps.pickups.tasks.flag_pickup_for_review.delay')
    def test_complete_clean_pickup(self, mock_flag, mock_notify, mock_award):
        """Standard valid completion logic ensuring reward assignments occur."""
        self.client.force_authenticate(user=self.worker)
        url = reverse('pickup-complete', kwargs={'pk': self.p1.id})
        data = {
            "waste_photo_url": "https://s3.local/img1.jpg",
            "ai_classification": "clean",
            "contamination_confidence": 0.95,
            "weight_kg": 5.5,
            "is_gps_override": False
        }
        res = self.client.patch(url, data, format='json')
        self.p1.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(self.p1.status, 'completed')
        self.assertEqual(self.p1.verification.ai_classification, "clean")
        
        # Verify async hooks executed
        mock_award.assert_called_once_with(self.p1.id)
        mock_notify.assert_called_once_with(self.p1.id)
        mock_flag.assert_not_called()

    @patch('apps.rewards.tasks.award_greenleaf_points.delay')
    @patch('apps.notifications.tasks.notify_resident_pickup_complete.delay')
    @patch('apps.pickups.tasks.flag_pickup_for_review.delay')
    def test_complete_contaminated_pickup(self, mock_flag, mock_notify, mock_award):
        """Worker forces a contaminated flag triggering an Admin Review trace."""
        self.client.force_authenticate(user=self.worker)
        url = reverse('pickup-complete', kwargs={'pk': self.p1.id})
        data = {
            "waste_photo_url": "https://s3.local/img2.jpg",
            "ai_classification": "contaminated",
            "contamination_confidence": 0.40,  # Below 0.70 limit
            "is_gps_override": True,
            "notes": "GPS jumped, forced completion with mixed waste."
        }
        res = self.client.patch(url, data, format='json')
        self.p1.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(self.p1.notes, "GPS jumped, forced completion with mixed waste.")
        self.assertTrue(self.p1.verification.requires_admin_review)
        
        mock_award.assert_called_once_with(self.p1.id)
        mock_flag.assert_called_once_with(self.p1.id)
