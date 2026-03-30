import pytest
from django.urls import reverse
from rest_framework import status
from tests.factories import UserFactory, RewardFactory, PickupFactory

@pytest.mark.django_db
class TestRewardAPI:
    def test_get_balance(self, api_client):
        resident = UserFactory(role='RESIDENT')
        api_client.force_authenticate(user=resident)
        
        # Create some rewards
        RewardFactory(resident=resident, points=10, transaction_type='EARNED')
        RewardFactory(resident=resident, points=5, transaction_type='EARNED')
        RewardFactory(resident=resident, points=-3, transaction_type='REDEEMED')
        
        url = reverse('reward-balance')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['balance'] == 12

    def test_get_history(self, api_client):
        resident = UserFactory(role='RESIDENT')
        api_client.force_authenticate(user=resident)
        
        pickup = PickupFactory(resident=resident)
        RewardFactory(resident=resident, points=10, transaction_type='EARNED', pickup=pickup)
        
        url = reverse('reward-history')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        # Assuming pagination is on, data might be in 'results'
        if 'results' in response.data:
            results = response.data['results']
        else:
            results = response.data
            
        assert len(results) >= 1
        assert results[0]['pickup'] == str(pickup.id)
