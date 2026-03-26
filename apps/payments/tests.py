from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from apps.users.models import User
from .models import FeeCollection

class PaymentsTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.worker = User.objects.create(email="worker@test.com", name="Worker", role="HKS_WORKER")
        self.resident = User.objects.create(email="resident@test.com", name="Resident", role="RESIDENT")
        self.client.force_authenticate(user=self.worker)
        self.payment_url = reverse('payment-list')

    def test_create_payment_auto_assigns_collector(self):
        """Test that payment record auto-assigns the worker who created it"""
        data = {
            "resident": self.resident.id,
            "amount": "50.00",
            "payment_method": "CASH"
        }
        response = self.client.post(self.payment_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        payment = FeeCollection.objects.get(id=response.data['id'])
        self.assertEqual(payment.collected_by, self.worker)
        self.assertTrue(payment.receipt_number.startswith("FC-"))

    def test_resident_only_sees_own_payments(self):
        """Test RBAC: Residents see only their own payments"""
        other_res = User.objects.create(email="other@test.com", name="Other", role="RESIDENT")
        FeeCollection.objects.create(resident=self.resident, amount=10, collected_by=self.worker)
        FeeCollection.objects.create(resident=other_res, amount=20, collected_by=self.worker)
        
        self.client.force_authenticate(user=self.resident)
        response = self.client.get(self.payment_url)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(float(response.data[0]['amount']), 10.0)
