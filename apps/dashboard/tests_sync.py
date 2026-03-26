import uuid
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from apps.users.models import User
from apps.routes.models import Route
from apps.pickups.models import Pickup
from apps.wards.models import Ward
from apps.dashboard.models import SyncQueue
from django.contrib.gis.geos import Point, LineString
from django.utils import timezone

class SyncOfflineTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.worker = User.objects.create(email="worker@test.com", name="Worker", role="HKS_WORKER")
        self.ward = Ward.objects.create(
            name="Ward 1", 
            number=1, 
            location=Point(0,0),
            boundary=Point(0,0).buffer(1)
        )
        self.route = Route.objects.create(
            hks_worker=self.worker, 
            ward=self.ward, 
            route_date=timezone.now().date(),
            planned_path=LineString((0,0), (1,1))
        )
        self.pickup = Pickup.objects.create(
            resident=User.objects.create(email=f"res_{uuid.uuid4()}@test.com", name="Res", role="RESIDENT"),
            ward=self.ward,
            location=Point(0.5, 0.5),
            waste_type="dry",
            status="pending"
        )
        self.client.force_authenticate(user=self.worker)
        self.prefetch_url = reverse('syncqueue-prefetch')
        self.push_url = reverse('syncqueue-push')

    def test_prefetch_data_bundle(self):
        """Test that prefetch returns route, pickups, and ward data"""
        response = self.client.get(self.prefetch_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(response.data['route'])
        # GeoFeatureModelSerializer returns a dict with 'features' for many=True
        self.assertEqual(len(response.data['pickups']['features']), 1)
        # But we manually wrapped the single ward in a list in the view
        self.assertEqual(len(response.data['wards']), 1)

    def test_bulk_push_mutations(self):
        """Test that worker can push multiple sync items at once"""
        data = [
            {
                "model_name": "Pickup",
                "object_id": str(self.pickup.id),
                "action": "UPDATE",
                "payload": {"status": "completed"}
            },
            {
                "model_name": "Route",
                "object_id": str(self.route.id),
                "action": "UPDATE",
                "payload": {"actual_path": "LINESTRING(0 0, 0.5 0.5)"}
            }
        ]
        response = self.client.post(self.push_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(SyncQueue.objects.filter(user=self.worker).count(), 2)

    def test_sync_queue_user_silo(self):
        """Test that sync items are siloed by user"""
        other_worker = User.objects.create(email="other@test.com", name="Other", role="HKS_WORKER")
        SyncQueue.objects.create(user=other_worker, model_name="Test", object_id="1", action="CREATE")
        
        response = self.client.get(reverse('syncqueue-list'))
        self.assertEqual(len(response.data), 0) # Only see their own
