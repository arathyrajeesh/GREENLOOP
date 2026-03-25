from rest_framework import serializers
from .models import MaterialType, RecyclerPurchase, RecyclingCertificate

class MaterialTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaterialType
        fields = '__all__'

class RecyclerPurchaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecyclerPurchase
        fields = '__all__'

class RecyclingCertificateSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecyclingCertificate
        fields = '__all__'
