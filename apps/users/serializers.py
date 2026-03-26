from rest_framework import serializers
from apps.users.models import User

class UserSerializer(serializers.ModelSerializer):
    points_balance = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'email', 'name', 'role', 'ward', 'is_active', 'created_at', 'points_balance']
        read_only_fields = ['id', 'created_at', 'points_balance']

    def get_points_balance(self, obj):
        if obj.role != 'RESIDENT':
            return None
        from apps.rewards.models import Reward
        from django.db.models import Sum
        return Reward.objects.filter(resident=obj).aggregate(Sum('points'))['points__sum'] or 0
