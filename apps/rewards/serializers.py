from rest_framework import serializers
from .models import Reward, RewardRedemption

class RewardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reward
        fields = '__all__'

class RewardRedemptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RewardRedemption
        fields = '__all__'
        read_only_fields = ['id', 'resident', 'status', 'created_at', 'updated_at']
