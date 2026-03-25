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
