import pytest
from django.urls import reverse
from rest_framework import status
from apps.recyclers.models import MaterialType, RecyclerPurchase, RecyclingCertificate
from tests.factories import (
    UserFactory, AdminFactory, WardFactory, 
    MaterialTypeFactory, RecyclerPurchaseFactory, 
    RecyclingCertificateFactory
)

@pytest.mark.django_db
class TestRecyclerPortal:
    def test_create_material_type(self, api_client):
        recycler = UserFactory(role='RECYCLER')
        api_client.force_authenticate(user=recycler)
        
        url = reverse('materialtype-list')
        data = {
            "name": "HDPE Plastic",
            "category": "Plastic",
            "unit": "kg",
            "price_per_unit": 20.0,
            "description": "High-density polyethylene"
        }
        
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert MaterialType.objects.filter(name="HDPE Plastic").exists()

    def test_create_purchase(self, api_client):
        recycler = UserFactory(role='RECYCLER')
        ward = WardFactory()
        material = MaterialTypeFactory(price_per_unit=15.0)
        api_client.force_authenticate(user=recycler)
        
        url = reverse('recyclerpurchase-list')
        data = {
            "material_type": material.id,
            "quantity": 100.0,
            "source_ward": ward.id
        }
        
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert float(response.data['total_price']) == 1500.0 
        assert RecyclerPurchase.objects.filter(recycler=recycler, quantity=100.0).exists()

    def test_request_certificate(self, api_client, mocker):
        # Mock Celery task
        mock_task = mocker.patch('apps.recyclers.tasks.generate_recycling_certificate_pdf.delay')
        
        recycler = UserFactory(role='RECYCLER')
        api_client.force_authenticate(user=recycler)
        
        # Create some purchases
        p1 = RecyclerPurchaseFactory(recycler=recycler)
        p2 = RecyclerPurchaseFactory(recycler=recycler)
        
        url = reverse('recycling-certificate-list')
        data = {
            "purchase_ids": [p1.id, p2.id],
            "metadata": {"batch": "Q1-Recycling"}
        }
        
        # Use format='json' for nested data
        response = api_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        
        cert = RecyclingCertificate.objects.get(certificate_number=response.data['certificate_number'])
        assert cert.status == 'PENDING'
        assert cert.purchases.count() == 2
        mock_task.assert_called_once_with(cert.id)

    def test_admin_verify_certificate(self, api_client, mocker):
        mock_notify = mocker.patch('apps.notifications.tasks.notify_recycler_certificate_verified.delay')
        
        admin = AdminFactory()
        recycler = UserFactory(role='RECYCLER')
        cert = RecyclingCertificateFactory(recycler=recycler, status='PENDING')
        
        api_client.force_authenticate(user=admin)
        
        url = reverse('recycling-certificate-verify', args=[cert.id])
        response = api_client.post(url)
        
        assert response.status_code == status.HTTP_200_OK
        cert.refresh_from_db()
        assert cert.status == 'VERIFIED'
        mock_notify.assert_called_once_with(cert.id)

    def test_non_admin_cannot_verify(self, api_client):
        recycler = UserFactory(role='RECYCLER')
        cert = RecyclingCertificateFactory(recycler=recycler, status='PENDING')
        
        api_client.force_authenticate(user=recycler)
        
        url = reverse('recycling-certificate-verify', args=[cert.id])
        response = api_client.post(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN
