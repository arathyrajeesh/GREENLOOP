from rest_framework import serializers
from apps.users.models import User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'name', 'role', 'ward', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']
