from rest_framework import serializers
from .models import OTPCode

class OTPCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = OTPCode
        fields = '__all__'
        read_only_fields = ['expires_at', 'is_used']

class OTPRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

class OTPVerifySerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    code = serializers.CharField(max_length=6, min_length=6, required=True)
