from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from apps.users.models import User
from .models import MaterialType, RecyclerPurchase, RecyclingCertificate

class RecyclersTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.recycler = User.objects.create(email="recycler@test.com", name="Recycler", role="RECYCLER")
        self.resident = User.objects.create(email="resident@test.com", name="Resident", role="RESIDENT")
        self.material = MaterialType.objects.create(name="Plastic", unit="kg", base_price=10.0)
        self.client.force_authenticate(user=self.recycler)
        
        self.purchase_url = reverse('recyclerpurchase-list')
        self.certificate_url = reverse('recycling-certificate-list')

    def test_create_purchase(self):
        """Test recycler can purchase material and price is calculated"""
        data = {
            "material_type": self.material.id,
            "weight_kg": 50
        }
        response = self.client.post(self.purchase_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        purchase = RecyclerPurchase.objects.get(id=response.data['id'])
        self.assertEqual(purchase.amount_paid, 500.0)
        self.assertEqual(purchase.recycler, self.recycler)

    def test_create_certificate(self):
        """Test recycler can issue a certificate and number is generated"""
        data = {
            "resident": self.resident.id,
            "metadata": {"weight": 10, "type": "PET"}
        }
        response = self.client.post(self.certificate_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        cert = RecyclingCertificate.objects.get(id=response.data['id'])
        self.assertTrue(cert.certificate_number.startswith("CERT-"))
        self.assertEqual(cert.recycler, self.recycler)
        self.assertEqual(cert.resident, self.resident)

    def test_recycler_only_sees_own_purchases(self):
        """Test RBAC: recyclers only see their own purchases"""
        RecyclerPurchase.objects.create(recycler=self.recycler, material_type=self.material, weight_kg=10, amount_paid=100)
        other_recycler = User.objects.create(email="other@test.com", name="Other", role="RECYCLER")
        RecyclerPurchase.objects.create(recycler=other_recycler, material_type=self.material, weight_kg=20, amount_paid=200)
        
        response = self.client.get(self.purchase_url)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(float(response.data[0]['weight_kg']), 10.0)
        
    def test_resident_sees_own_certificates(self):
        """Test RBAC: residents can see certificates issued to them"""
        RecyclingCertificate.objects.create(resident=self.resident, recycler=self.recycler, certificate_number="CERT-123")
        
        self.client.force_authenticate(user=self.resident)
        response = self.client.get(self.certificate_url)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['certificate_number'], "CERT-123")
