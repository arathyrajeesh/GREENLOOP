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
        self.push_url = reverse('syncqueue-upload')

    def test_prefetch_data_bundle(self):
        """Test that prefetch returns route, pickups, and ward data"""
        response = self.client.get(self.prefetch_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(response.data['route'])
        # GeoFeatureModelSerializer returns a dict with 'features' for many=True
        self.assertEqual(len(response.data['pickups']['features']), 1)
        # But we manually wrapped the single ward in a list in the view
        self.assertEqual(len(response.data['wards']), 1)

    def test_bulk_upload(self):
        """Test that worker can upload multiple sync items at once"""
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
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['items']), 2)
        self.assertEqual(SyncQueue.objects.filter(user=self.worker).count(), 2)

    def test_sync_queue_user_silo(self):
        """Test that sync items are siloed by user"""
        other_worker = User.objects.create(email="other@test.com", name="Other", role="HKS_WORKER")
        SyncQueue.objects.create(user=other_worker, model_name="Test", object_id="1", action="CREATE")
        
        response = self.client.get(reverse('syncqueue-list'))
        self.assertEqual(len(response.data), 0) # Only see their own

    def test_upload_chronological_processing(self):
        """Test that items are processed in chronological order based on client_timestamp"""
        upload_url = reverse('syncqueue-upload')
        c_id1 = uuid.uuid4()
        c_id2 = uuid.uuid4()
        data = [
            {
                "client_id": str(c_id2),
                "client_timestamp": "2026-03-26T12:00:00Z",
                "model_name": "Pickup",
                "object_id": str(self.pickup.id),
                "action": "UPDATE",
                "payload": {"status": "completed"}
            },
            {
                "client_id": str(c_id1),
                "client_timestamp": "2026-03-26T11:00:00Z",
                "model_name": "Pickup",
                "object_id": str(self.pickup.id),
                "action": "UPDATE",
                "payload": {"status": "accepted"}
            }
        ]
        # Although uploaded in order (c_id2, c_id1), c_id1 has an earlier timestamp.
        # But wait, our current logic just creates them. The final state of the pickup should reflect the LATEST valid update.
        response = self.client.post(upload_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify pickup final state is 'completed' (from c_id2)
        self.pickup.refresh_from_db()
        self.assertEqual(self.pickup.status, 'completed')

    def test_upload_conflict_detection(self):
        """Test that completing a cancelled pickup flags a conflict"""
        upload_url = reverse('syncqueue-upload')
        self.pickup.status = 'cancelled'
        self.pickup.save()
        
        data = [{
            "client_id": str(uuid.uuid4()),
            "client_timestamp": timezone.now().isoformat(),
            "model_name": "Pickup",
            "object_id": str(self.pickup.id),
            "action": "UPDATE",
            "payload": {"status": "completed"}
        }]
        response = self.client.post(upload_url, data, format='json')
        self.assertEqual(response.data['items'][0]['status'], 'CONFLICT')
        self.assertIn("admin-cancelled", response.data['items'][0]['conflict_reason'])

    def test_upload_idempotency(self):
        """Test that re-uploading the same client_id is skipped"""
        upload_url = reverse('syncqueue-upload')
        c_id = uuid.uuid4()
        data = [{
            "client_id": str(c_id),
            "client_timestamp": timezone.now().isoformat(),
            "model_name": "Pickup",
            "object_id": str(self.pickup.id),
            "action": "UPDATE",
            "payload": {"status": "completed"}
        }]
        # First upload
        self.client.post(upload_url, data, format='json')
        # Second upload
        response = self.client.post(upload_url, data, format='json')
        self.assertEqual(response.data['items'][0]['message'], "Already processed")
        self.assertEqual(SyncQueue.objects.filter(client_id=c_id).count(), 1)
