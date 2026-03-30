from rest_framework import serializers
from .models import Reward, RewardRedemption, RewardItem, RewardSettings

class RewardSerializer(serializers.ModelSerializer):
    pickup_type = serializers.CharField(source='pickup.waste_type', read_only=True)

    class Meta:
        model = Reward
        fields = ['id', 'resident', 'points', 'transaction_type', 'description', 'pickup', 'pickup_type', 'running_balance', 'created_at']

class RewardItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = RewardItem
        fields = '__all__'

class RewardSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = RewardSettings
        fields = '__all__'

class RewardRedemptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RewardRedemption
        fields = '__all__'
        read_only_fields = ['id', 'resident', 'status', 'created_at', 'updated_at']
