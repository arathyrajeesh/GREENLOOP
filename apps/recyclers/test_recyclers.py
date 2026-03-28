import pytest
from django.urls import reverse
from rest_framework import status
from tests.factories import UserFactory

@pytest.mark.django_db
class TestRecyclerViewSet:
    def test_list_material_types(self, admin_client):
        url = reverse('materialtype-list')
        response = admin_client.get(url)
        assert response.status_code == status.HTTP_200_OK

@pytest.mark.django_db
class TestRecyclerPurchase:
    def test_list_purchases(self, admin_client):
        url = reverse('recyclerpurchase-list')
        response = admin_client.get(url)
        assert response.status_code == status.HTTP_200_OK
