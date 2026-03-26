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
            "has_vest": True
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
        }
        
        response = self.client.post(self.attendance_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], "Check-in Location is outside the assigned ward boundary")
        
        # Ensure no log created
        self.assertFalse(AttendanceLog.objects.filter(worker=self.worker2).exists())
