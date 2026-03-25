from rest_framework import serializers
from .models import OTPCode

class OTPCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = OTPCode
        fields = '__all__'
        read_only_fields = ['expires_at', 'is_used']
