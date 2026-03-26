from rest_framework import serializers
from .models import FeeCollection

class FeeCollectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeeCollection
        fields = '__all__'
        read_only_fields = ['id', 'receipt_number', 'collected_by', 'payment_date']
