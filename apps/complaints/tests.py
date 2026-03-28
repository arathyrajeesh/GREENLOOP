from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from apps.users.models import User
from apps.complaints.models import Complaint
from django.contrib.gis.geos import Point

class ComplaintsTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.resident = User.objects.create(email="res@test.com", name="Resident", role="RESIDENT")
        self.admin = User.objects.create(email="admin@test.com", name="Admin", role="ADMIN")
        self.client.force_authenticate(user=self.resident)
        self.complaint_url = reverse('complaint-list')

    def test_create_complaint(self):
        """Test resident can create a complaint and it gets auto-assigned to them"""
        data = {
            "category": "PICKUP",
            "description": "My waste was not collected today.",
            "location": {"type": "Point", "coordinates": [77.5946, 12.9716]}
        }
        response = self.client.post(self.complaint_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        complaint = Complaint.objects.get(id=response.data['id'])
        self.assertEqual(complaint.reporter, self.resident)
        self.assertEqual(complaint.status, "submitted")

    def test_resident_only_sees_own_complaints(self):
        """Test RBAC: residents only see their own complaints"""
        Complaint.objects.create(reporter=self.resident, category="PICKUP", description="My complaint")
        other_user = User.objects.create(email="other@test.com", name="Other", role="RESIDENT")
        Complaint.objects.create(reporter=other_user, category="CLEANLINESS", description="Other complaint")
        
        response = self.client.get(self.complaint_url)
        # GeoFeatureModelSerializer response has 'features' key
        self.assertEqual(len(response.data['features']), 1)
        self.assertEqual(response.data['features'][0]['properties']['description'], "My complaint")

    def test_admin_sees_all_complaints(self):
        """Test RBAC: admins can see all complaints"""
        Complaint.objects.create(reporter=self.resident, category="PICKUP", description="Res complaint")
        other_user = User.objects.create(email="other@test.com", name="Other", role="RESIDENT")
        Complaint.objects.create(reporter=other_user, category="CLEANLINESS", description="Other complaint")
        
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(self.complaint_url)
        self.assertEqual(len(response.data['features']), 2)
