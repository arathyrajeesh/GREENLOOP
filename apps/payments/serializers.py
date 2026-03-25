from rest_framework import serializers
from .models import FeeCollection

class FeeCollectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeeCollection
        fields = '__all__'
        read_only_fields = ['receipt_number']
