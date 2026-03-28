import pytest
from django.urls import reverse
from rest_framework import status
from tests.factories import ResidentFactory, WorkerFactory

@pytest.mark.django_db
class TestFeeCollectionViewSet:
    def test_list_payments_resident(self, authenticated_client, resident_user):
        url = reverse('payment-list')
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_summary_worker(self, worker_client, worker_user):
        url = reverse('payment-summary')
        response = worker_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert 'total_collected' in response.data
