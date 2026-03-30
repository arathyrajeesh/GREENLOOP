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

class BaseResponseSerializer(serializers.Serializer):
    message = serializers.CharField()

class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()

class WorkerLoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True, help_text="Email or Username")
    password = serializers.CharField(write_only=True, required=True)

class AdminLoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True, help_text="Administrator's registered email")
    password = serializers.CharField(write_only=True, required=True)
