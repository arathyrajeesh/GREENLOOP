import pytest
from django.urls import reverse
from rest_framework import status

@pytest.mark.django_db
class TestReportViewSet:
    def test_list_report_categories(self, admin_client):
        url = reverse('reportcategory-list')
        response = admin_client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_list_reports(self, admin_client):
        url = reverse('report-list')
        response = admin_client.get(url)
        assert response.status_code == status.HTTP_200_OK
