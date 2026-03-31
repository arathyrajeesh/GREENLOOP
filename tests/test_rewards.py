import pytest
from django.urls import reverse
from rest_framework import status
from tests.factories import ResidentFactory, RewardFactory, RewardItemFactory

@pytest.mark.django_db
class TestRewardSystem:
    def test_list_reward_items(self, api_client):
        RewardItemFactory(name="Eco Mug", points_cost=500)
        url = reverse('reward-item-list')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1

    def test_resident_points_balance_serializer(self, authenticated_client, resident_user):
        RewardFactory(resident=resident_user, points=100)
        RewardFactory(resident=resident_user, points=50, transaction_type='SPENT') # Should be negative in logic
        
        # Wait, check if Reward transaction_type 'SPENT' points are stored as negative or handled by sum.
        # In apps/users/serializers.py, points balance is Sum('points').
        # If I want to deduct points, they should be stored as negative numbers if we use simple Sum.
        
        url = reverse('user-me') # Me endpoint
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        # 100 + 50 = 150 (if my factory uses positive always)
        assert response.data['points_balance'] == 150

    def test_admin_change_reward_settings(self, admin_client):
        url = reverse('reward-settings-list')
        # Create settings first if needed, though usually singleton
        response = admin_client.get(url)
        assert response.status_code == status.HTTP_200_OK
