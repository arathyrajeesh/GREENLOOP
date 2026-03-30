import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from apps.contamination_review.models import Pickup
from django.core.files.uploadedfile import SimpleUploadedFile

from tests.factories import AdminFactory

@pytest.fixture
def api_client():
    client = APIClient()
    admin = AdminFactory()
    client.force_authenticate(user=admin)
    return client

@pytest.fixture
def dummy_image():
    # Create a simple valid 1x1 GIF image for ImageField testing
    return SimpleUploadedFile(
        name='test_image.gif',
        content=b'GIF89a\x01\x00\x01\x00\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;',
        content_type='image/gif'
    )

@pytest.mark.django_db
class TestContaminationReview:
    
    def test_create_clean_pickup(self, api_client, dummy_image):
        url = reverse('create-pickup')
        data = {
            'image': dummy_image,
            'ai_classification': 'clean',
            'confidence_score': 0.85,
            'points_awarded': 10
        }
        response = api_client.post(url, data, format='multipart')
        
        assert response.status_code == status.HTTP_201_CREATED
        pickup = Pickup.objects.get(id=response.data['id'])
        
        # Clean with high confidence shouldn't need review based on our logic (>= 0.7)
        assert pickup.needs_review is False
        assert pickup.contamination_flag is False

    def test_create_contaminated_pickup_high_confidence(self, api_client, dummy_image):
        url = reverse('create-pickup')
        data = {
            'image': dummy_image,
            'ai_classification': 'contaminated',
            'confidence_score': 0.90,
            'points_awarded': 5
        }
        response = api_client.post(url, data, format='multipart')
        
        assert response.status_code == status.HTTP_201_CREATED
        pickup = Pickup.objects.get(id=response.data['id'])
        
        # Contaminated and >=0.7 confidence -> flags are set to True
        assert pickup.needs_review is True
        assert pickup.contamination_flag is True

    def test_create_pickup_low_confidence(self, api_client, dummy_image):
        url = reverse('create-pickup')
        data = {
            'image': dummy_image,
            'ai_classification': 'clean',
            'confidence_score': 0.50,
            'points_awarded': 10
        }
        response = api_client.post(url, data, format='multipart')
        
        assert response.status_code == status.HTTP_201_CREATED
        pickup = Pickup.objects.get(id=response.data['id'])
        
        # Low confidence (<0.7) always needs review regardless of classification
        assert pickup.needs_review is True
        assert pickup.contamination_flag is False
        
    def test_get_review_queue(self, api_client, dummy_image):
        # Create a flagged and an unflagged item directly
        needs_review_item = Pickup.objects.create(
            image='test_image.gif', ai_classification='contaminated',
            confidence_score=0.9, needs_review=True, contamination_flag=True, points_awarded=5
        )
        clean_item = Pickup.objects.create(
            image='test_image2.gif', ai_classification='clean',
            confidence_score=0.9, needs_review=False, contamination_flag=False, points_awarded=10
        )
        
        url = reverse('review-queue')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]['id'] == needs_review_item.id

    def test_confirm_pickup(self, api_client):
        item = Pickup.objects.create(
            image='test_image.gif', ai_classification='contaminated',
            confidence_score=0.9, needs_review=True, contamination_flag=True, points_awarded=5
        )
        
        url = reverse('confirm-pickup', kwargs={'pk': item.id})
        response = api_client.post(url)
        
        assert response.status_code == status.HTTP_200_OK
        item.refresh_from_db()
        
        # Confirmed -> no longer needs review, points stand, flag stands
        assert item.needs_review is False
        assert item.contamination_flag is True
        assert item.points_awarded == 5

    def test_override_clean_pickup(self, api_client):
        item = Pickup.objects.create(
            image='test_image.gif', ai_classification='contaminated',
            confidence_score=0.8, needs_review=True, contamination_flag=True, points_awarded=5
        )
        
        url = reverse('override-clean', kwargs={'pk': item.id})
        response = api_client.post(url)
        
        assert response.status_code == status.HTTP_200_OK
        item.refresh_from_db()
        
        # Overridden to Clean -> no longer needs review, flag cleared, points +5
        assert item.needs_review is False
        assert item.contamination_flag is False
        assert item.points_awarded == 10
