from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from django.utils import timezone
from django.contrib.gis.geos import Point, LineString
from apps.users.models import User
from apps.wards.models import Ward
from apps.routes.models import Route
from apps.pickups.models import Pickup
from apps.attendance.models import AttendanceLog

class HKSEndpointsTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        
        # Create Ward with a known square boundary from (0,0) to (10,10)
        self.ward = Ward.objects.create(
            name="Testing Ward GIS", 
            number=99,
            location=Point(5, 5),
            boundary="POLYGON((0 0, 0 10, 10 10, 10 0, 0 0))"
        )
        
        # Create Users
        self.worker = User.objects.create(email="worker1@hks.com", name="Worker 1", role="HKS_WORKER", ward=self.ward)
        self.worker2 = User.objects.create(email="worker2@hks.com", name="Worker 2", role="HKS_WORKER", ward=self.ward)
        self.resident = User.objects.create(email="res1@hks.com", name="Res 1", role="RESIDENT", ward=self.ward)
        
        self.route_today_url = reverse('hks-route-today')
        self.attendance_url = reverse('hks-attendance')
        
    def test_today_route_unassigned(self):
        """Test getting today's route when none is assigned yields 404"""
        self.client.force_authenticate(user=self.worker)
        response = self.client.get(self.route_today_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data['message'], 'No route assigned for today')

    def test_today_route_assigned_with_pickups(self):
        """Test fetching an assigned route returns the linestring and ordered pickups"""
        today = timezone.now().date()
        
        # Create a route for today
        route = Route.objects.create(
            hks_worker=self.worker,
            ward=self.ward,
            route_date=today,
            planned_path=LineString((1, 1), (2, 2), (3, 3))
        )
        
        # Create some pickups for today in the same ward
        p1 = Pickup.objects.create(
            resident=self.resident, ward=self.ward, waste_type="dry", 
            location=Point(2, 2), scheduled_date=today, time_slot="10:00-12:00",
            status="pending"
        )
        p2 = Pickup.objects.create(
            resident=self.resident, ward=self.ward, waste_type="wet", 
            location=Point(3, 3), scheduled_date=today, time_slot="08:00-10:00",
            status="accepted"
        )
        
        # A pickup for tomorrow that shouldn't appear
        Pickup.objects.create(
            resident=self.resident, ward=self.ward, waste_type="hazardous", 
            location=Point(4, 4), scheduled_date=today + timezone.timedelta(days=1), time_slot="08:00-10:00"
        )
        
        self.client.force_authenticate(user=self.worker)
        response = self.client.get(self.route_today_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check Route Serialization
        self.assertEqual(response.data['route']['id'], route.id)
        # Check ordered pickups (08:00 should be before 10:00)
        features = response.data['pickups']['features']
        self.assertEqual(len(features), 2)
        self.assertEqual(features[0]['id'], str(p2.id))
        self.assertEqual(features[1]['id'], str(p1.id))

    def test_attendance_inside_boundary(self):
        """Test attendance login with GPS inside the boundary works successfully"""
        self.client.force_authenticate(user=self.worker)
        data = {
            "check_in_location": {"type": "Point", "coordinates": [5.0, 5.0]}, # Inside (0,0) to (10,10)
            "ppe_photo_url": "https://example.com/photo.jpg",
            "has_vest": True,
            "has_mask": True,
            "has_gloves": True,
            "has_boots": True,
        }
        
        response = self.client.post(self.attendance_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        log = AttendanceLog.objects.get(worker=self.worker, date=timezone.now().date())
        self.assertIsNotNone(log.check_in)
        self.assertEqual(log.ppe_photo_url, "https://example.com/photo.jpg")
        self.assertTrue(log.has_vest)
        
    def test_attendance_outside_boundary(self):
        """Test attendance login with GPS purely outside the boundary is rejected"""
        self.client.force_authenticate(user=self.worker2)
        data = {
            "check_in_location": {"type": "Point", "coordinates": [11.0, 11.0]}, # Outside (0,0) to (10,10)
            "ppe_photo_url": "https://example.com/photo.jpg",
            "has_vest": True,
            "has_mask": True,
            "has_gloves": True,
            "has_boots": True,
        }
        
        response = self.client.post(self.attendance_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], "Check-in Location is outside the assigned ward boundary")
        
        # Ensure no log created
        self.assertFalse(AttendanceLog.objects.filter(worker=self.worker2).exists())

    def test_attendance_missing_ppe(self):
        """Test attendance rejected if PPE checklist is incomplete"""
        self.client.force_authenticate(user=self.worker)
        data = {
            "check_in_location": {"type": "Point", "coordinates": [5.0, 5.0]},
            "ppe_photo_url": "https://example.com/photo.jpg",
            "has_vest": True,
            "has_mask": True,
            "has_gloves": False, # Missing gloves
            "has_boots": True,
        }
        response = self.client.post(self.attendance_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], "All PPE items must be confirmed for check-in")

    def test_attendance_checkout(self):
        """Test worker checkout mutation securely closes the day log"""
        today = timezone.now().date()
        AttendanceLog.objects.create(
            worker=self.worker,
            date=today,
            check_in=timezone.now().time(),
            check_in_location=Point(5.0, 5.0)
        )
        self.client.force_authenticate(user=self.worker)
        response = self.client.patch(self.attendance_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        log = AttendanceLog.objects.get(worker=self.worker, date=today)
        self.assertIsNotNone(log.check_out)

    def test_attendance_history(self):
        """Test fetching monthly attendance calendar works with date filters"""
        now = timezone.now()
        AttendanceLog.objects.create(
            worker=self.worker,
            date=now.date(),
            check_in=now.time(),
            check_in_location=Point(5.0, 5.0)
        )
        
        # Log for previous month
        prev_month = now - timezone.timedelta(days=32)
        AttendanceLog.objects.create(
            worker=self.worker,
            date=prev_month.date(),
            check_in=prev_month.time(),
            check_in_location=Point(5.0, 5.0)
        )
        
        self.client.force_authenticate(user=self.worker)
        
        # Test default (current month)
        response = self.client.get(self.attendance_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should only return current month log
        features_default = response.data.get('features', [])
        self.assertEqual(len(features_default), 1)
        self.assertEqual(features_default[0]['properties']['date'], str(now.date()))
        
        # Test specific month
        month_str = f"{prev_month.year}-{prev_month.month:02d}"
        response_prev = self.client.get(f"{self.attendance_url}?month={month_str}")
        self.assertEqual(response_prev.status_code, status.HTTP_200_OK)
        features_prev = response_prev.data.get('features', [])
        self.assertEqual(len(features_prev), 1)
        self.assertEqual(features_prev[0]['properties']['date'], str(prev_month.date()))
