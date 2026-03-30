import pytest
from django.urls import reverse
from rest_framework import status
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.reports.models import WardCollectionReport

from tests.factories import (
    UserFactory, AdminFactory, WardFactory, 
    PickupFactory, RecyclerPurchaseFactory
)

@pytest.mark.django_db
class TestWardCollectionReport:
    def test_create_report_as_admin(self, api_client, mocker):
        # Mock the celery task
        mock_task = mocker.patch('apps.reports.tasks.generate_ward_collection_report.delay')
        
        admin = AdminFactory()
        ward = WardFactory()
        api_client.force_authenticate(user=admin)
        
        url = reverse('wardcollectionreport-list')
        data = {
            "ward": ward.id,
            "start_date": "2023-01-01",
            "end_date": "2023-01-31"
        }
        
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['status'] == 'PENDING'
        assert response.data['generated_by'] == admin.id
        
        report = WardCollectionReport.objects.last()
        mock_task.assert_called_once_with(report.id)

    def test_non_admin_cannot_create_report(self, api_client):
        resident = UserFactory(role='RESIDENT')
        ward = WardFactory()
        api_client.force_authenticate(user=resident)
        
        url = reverse('wardcollectionreport-list')
        data = {
            "ward": ward.id,
            "start_date": "2023-01-01",
            "end_date": "2023-01-31"
        }
        
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_generate_report_task(self, mocker):
        from apps.reports.tasks import generate_ward_collection_report
        
        # Mock the WeasyPrint HTML to avoid full PDF rendering in unit test
        mock_html = mocker.patch('apps.reports.tasks.HTML')
        # Mock HTML().write_pdf()
        mock_html.return_value.write_pdf.return_value = b'test_pdf_content'
        
        # Mock notification so it doesn't fail
        mock_notify = mocker.patch('apps.notifications.tasks.notify_admin_report_ready.delay')

        admin = AdminFactory()
        ward = WardFactory()
        
        # Add some data to test aggregations
        PickupFactory(ward=ward, status='completed')
        PickupFactory(ward=ward, status='pending')
        RecyclerPurchaseFactory(source_ward=ward)
        
        report = WardCollectionReport.objects.create(
            ward=ward,
            start_date="2023-01-01",
            end_date="2023-01-31",
            generated_by=admin
        )
        
        result = generate_ward_collection_report(report.id)
        assert "Success:" in result
        
        report.refresh_from_db()
        assert report.status == 'COMPLETED'
        assert bool(report.pdf_file) is True
        assert bool(report.csv_file) is True
        
        mock_notify.assert_called_once_with(report.id)
