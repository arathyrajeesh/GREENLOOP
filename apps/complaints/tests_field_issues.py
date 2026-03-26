from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from apps.users.models import User
from apps.complaints.models import Complaint
from apps.notifications.models import Notification
from django.contrib.gis.geos import Point

class FieldIssueReportingTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create(email="admin@test.com", name="Admin", role="ADMIN")
        self.worker = User.objects.create(email="worker@test.com", name="Worker", role="HKS_WORKER")
        self.client.force_authenticate(user=self.worker)
        self.complaint_url = reverse('complaint-list')

    def test_worker_reports_field_issue(self):
        """Test that worker can report issues with categories like BLOCKED or OVERFLOW"""
        data = {
            "category": "BLOCKED",
            "description": "Resident's gate is locked, cannot access bins.",
            "location": {"type": "Point", "coordinates": [77.5946, 12.9716]}
        }
        response = self.client.post(self.complaint_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        complaint = Complaint.objects.get(id=response.data['id'])
        self.assertEqual(complaint.reporter, self.worker)
        self.assertEqual(complaint.category, "BLOCKED")

    def test_worker_sees_only_own_reports(self):
        """Test RBAC: Workers see only their own reports"""
        other_worker = User.objects.create(email="other@test.com", name="Other", role="HKS_WORKER")
        Complaint.objects.create(reporter=self.worker, category="OVERFLOW", description="Bins full")
        Complaint.objects.create(reporter=other_worker, category="PICKUP", description="Other's")
        
        response = self.client.get(self.complaint_url)
        # GeoFeatureModelSerializer response has 'features' key
        self.assertEqual(len(response.data['features']), 1)
        self.assertEqual(response.data['features'][0]['properties']['category'], "OVERFLOW")

    def test_admin_notification_on_complaint(self):
        """Test that a notification is created for the admin (synchronously in tests usually if not using celery e-b)"""
        # Since we use delay(), in regular Django tests without custom setup, it might not run unless forced.
        # But our task creates a Notification object.
        from apps.notifications.tasks import notify_admin_new_complaint
        complaint = Complaint.objects.create(reporter=self.worker, category="UNAVAILABLE", description="Not home")
        
        notify_admin_new_complaint(complaint.id) # Run synchronously for test
        
        self.assertTrue(Notification.objects.filter(user=self.admin).exists())
        notif = Notification.objects.get(user=self.admin)
        self.assertIn("Resident Unavailable", notif.title)
