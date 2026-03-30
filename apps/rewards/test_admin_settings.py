import pytest
from django.urls import reverse
from rest_framework import status
from apps.rewards.models import RewardSettings, Reward
from apps.pickups.models import Pickup
from apps.rewards.tasks import award_greenleaf_points
from tests.factories import AdminFactory, ResidentFactory, PickupFactory, PickupVerificationFactory

@pytest.mark.django_db
class TestAdminRewardSettings:
    def test_admin_can_update_settings(self, api_client):
        admin = AdminFactory()
        api_client.force_authenticate(user=admin)
        
        url = reverse('reward-settings-list')
        data = {
            "clean_pickup_points": 15,
            "contaminated_pickup_points": 7,
            "streak_bonus_points": 75,
            "streak_threshold_weeks": 6
        }
        
        response = api_client.post(url, data) # 'create' handles update for current settings
        assert response.status_code == status.HTTP_200_OK
        assert response.data['clean_pickup_points'] == 15
        
        settings = RewardSettings.get_settings()
        assert settings.clean_pickup_points == 15

    def test_non_admin_cannot_update_settings(self, api_client):
        resident = ResidentFactory()
        api_client.force_authenticate(user=resident)
        
        url = reverse('reward-settings-list')
        response = api_client.post(url, {"clean_pickup_points": 20})
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_dynamic_point_awarding(self, db):
        # 1. Update settings
        settings = RewardSettings.get_settings()
        settings.clean_pickup_points = 25
        settings.save()
        
        # 2. Create pickuup
        resident = ResidentFactory()
        pickup = PickupFactory(resident=resident, status='completed')
        PickupVerificationFactory(pickup=pickup, contamination_flag=False)
        
        # 3. Run task
        award_greenleaf_points(pickup.id)
        
        # 4. Verify points
        reward = Reward.objects.get(pickup=pickup)
        assert reward.points == 25

    def test_reward_item_management(self, api_client):
        admin = AdminFactory()
        api_client.force_authenticate(user=admin)
        
        url = reverse('reward-item-list')
        data = {
            "name": "Composting Kit",
            "description": "Start your home composting",
            "points_cost": 250
        }
        
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == "Composting Kit"
