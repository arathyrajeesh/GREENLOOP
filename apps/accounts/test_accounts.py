import pytest
from django.urls import reverse
from rest_framework import status
from apps.accounts.models import OTPCode
from unittest.mock import patch

@pytest.mark.django_db
class TestOTPAuth:
    @patch('apps.accounts.views.send_resend_email', return_value=True)
    def test_otp_request_success(self, mock_send, api_client, resident_user):
        url = reverse('otp_request')
        data = {"email": resident_user.email}
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_200_OK
        assert OTPCode.objects.filter(user=resident_user).exists()

    def test_otp_verify_success(self, api_client, resident_user):
        otp = OTPCode.objects.create(user=resident_user, code="123456")
        url = reverse('otp_verify')
        data = {"email": resident_user.email, "code": "123456"}
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data

@pytest.mark.django_db
class TestWorkerLogin:
    def test_worker_login_success(self, api_client, worker_user):
        worker_user.set_password("password123")
        worker_user.save()
        
        url = reverse('worker_login')
        data = {"username": worker_user.username, "password": "password123"}
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data

@pytest.mark.django_db
class TestAuthViews:
    def test_ping(self, api_client):
        url = reverse('ping')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'ok'

    def test_logout(self, authenticated_client, resident_user):
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = str(RefreshToken.for_user(resident_user))
        
        url = reverse('logout')
        data = {"refresh": refresh}
        response = authenticated_client.post(url, data)
        assert response.status_code == status.HTTP_200_OK

    def test_migrate(self, admin_client):
        url = reverse('migrate')
        response = admin_client.get(url)
        assert response.status_code == status.HTTP_200_OK
