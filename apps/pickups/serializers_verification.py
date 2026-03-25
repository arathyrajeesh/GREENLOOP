from rest_framework import serializers
from .models import PickupVerification

class PickupVerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PickupVerification
        fields = '__all__'
        read_only_fields = ['verified_at']
