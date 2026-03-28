import pytest
from django.urls import reverse
from rest_framework import status
from apps.users.models import User

@pytest.mark.django_db
class TestUserViewSet:
    def test_list_users_authenticated(self, admin_client):
        url = reverse('user-list')
        response = admin_client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_list_users_unauthenticated(self, api_client):
        url = reverse('user-list')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_retrieve_user_self(self, authenticated_client, resident_user):
        url = reverse('user-detail', kwargs={'pk': resident_user.pk})
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK

@pytest.mark.django_db
class TestWorkerRecyclerCreateAPIView:
    def test_create_worker_admin(self, admin_client, ward):
        url = reverse('create-worker')
        data = {
            "username": "newworker",
            "email": "newworker@test.com",
            "name": "New Worker",
            "password": "password123",
            "role": "HKS_WORKER",
            "ward": ward.id
        }
        # Assuming WorkerRecyclerCreateSerializer handles these fields
        response = admin_client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert User.objects.filter(email="newworker@test.com").exists()

    def test_create_worker_non_admin(self, authenticated_client):
        url = reverse('create-worker')
        data = {
            "email": "fail@test.com",
            "name": "Fail",
            "password": "password123",
            "role": "HKS_WORKER"
        }
        response = authenticated_client.post(url, data)
        assert response.status_code == status.HTTP_403_FORBIDDEN
