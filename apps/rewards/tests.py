from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from apps.users.models import User
from apps.rewards.models import Reward, RewardRedemption

class RewardsTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.resident = User.objects.create(email="res@test.com", name="Resident", role="RESIDENT")
        self.client.force_authenticate(user=self.resident)
        
        # Reward items URLs are not explicitly defined as a separate model in serializers, 
        # using the ModelViewSet registered in router.
        self.reward_list_url = reverse('reward-list')
        self.redemption_list_url = reverse('reward-redemption-list')
        self.profile_url = reverse('user-detail', kwargs={'pk': self.resident.pk})

    def test_points_balance_calculation(self):
        """Test that user profile shows correct points balance"""
        Reward.objects.create(resident=self.resident, points=100, transaction_type='EARNED', description="Pickup")
        Reward.objects.create(resident=self.resident, points=50, transaction_type='EARNED', description="Bonus")
        
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['points_balance'], 150)

    def test_redemption_success(self):
        """Test successful reward redemption with enough points"""
        Reward.objects.create(resident=self.resident, points=200, transaction_type='EARNED')
        
        data = {
            "reward_item": "Movie Ticket",
            "points_spent": 150
        }
        response = self.client.post(self.redemption_list_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Check balance after redemption
        profile_resp = self.client.get(self.profile_url)
        self.assertEqual(profile_resp.data['points_balance'], 50)
        
        # Verify Reward transaction was created
        self.assertTrue(Reward.objects.filter(resident=self.resident, transaction_type='REDEEMED', points=-150).exists())

    def test_redemption_insufficient_points(self):
        """Test redemption fails if points are not enough"""
        Reward.objects.create(resident=self.resident, points=100, transaction_type='EARNED')
        
        data = {
            "reward_item": "Expensive Prize",
            "points_spent": 150
        }
        response = self.client.post(self.redemption_list_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Insufficient points balance", str(response.data))
