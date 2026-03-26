from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from apps.users.models import User
from apps.payments.models import FeeCollection
from apps.pickups.models import Pickup
from apps.wards.models import Ward
from django.contrib.gis.geos import Point, Polygon

class FeeCollectionSummaryTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.ward = Ward.objects.create(
            name="Test Ward", 
            number=1, 
            location=Point(77.5946, 12.9716),
            boundary=Polygon(((0,0), (0,1), (1,1), (1,0), (0,0)))
        )
        self.worker = User.objects.create(email="worker@test.com", name="Worker", role="HKS_WORKER", ward=self.ward)
        self.resident1 = User.objects.create(email="res1@test.com", name="Res1", role="RESIDENT", ward=self.ward)
        self.resident2 = User.objects.create(email="res2@test.com", name="Res2", role="RESIDENT", ward=self.ward)
        self.client.force_authenticate(user=self.worker)
        
        self.payment_url = reverse('payment-list')
        self.summary_url = reverse('payment-summary')

    def test_daily_summary(self):
        """Test daily summary aggregation logic"""
        FeeCollection.objects.create(resident=self.resident1, ward=self.ward, amount=100.0, payment_method='CASH', collected_by=self.worker)
        FeeCollection.objects.create(resident=self.resident1, ward=self.ward, amount=50.0, payment_method='UPI', collected_by=self.worker)
        FeeCollection.objects.create(resident=self.resident2, ward=self.ward, amount=75.0, payment_method='CASH', collected_by=self.worker)
        
        response = self.client.get(self.summary_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(float(response.data['total_collected']), 225.0)
        self.assertEqual(response.data['household_count'], 2)
        self.assertEqual(response.data['payment_mode_breakdown']['CASH']['count'], 2)
        self.assertEqual(response.data['payment_mode_breakdown']['UPI']['count'], 1)

    def test_weight_threshold_payment_flag(self):
        """Test that weight > 50kg returns payment_required=True"""
        pickup = Pickup.objects.create(
            resident=self.resident1,
            ward=self.ward,
            location=Point(77.5946, 12.9716),
            status='pending',
            scheduled_date='2026-03-26'
        )
        
        data = {
            "weight_kg": 60,
            "ai_classification": "dry",
            "contamination_confidence": 0.9,
            "distance_meters": 10
        }
        response = self.client.patch(f"/api/v1/pickups/{pickup.id}/complete/", data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['payment_required'])
        self.assertIn("Fee collection required", response.data['message'])

    def test_weight_threshold_no_payment_flag(self):
        """Test that weight <= 50kg returns payment_required=False"""
        pickup = Pickup.objects.create(
            resident=self.resident1,
            ward=self.ward,
            location=Point(77.5946, 12.9716),
            status='pending'
        )
        
        data = {"weight_kg": 25}
        response = self.client.patch(f"/api/v1/pickups/{pickup.id}/complete/", data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['payment_required'])
