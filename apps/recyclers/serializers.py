from rest_framework import serializers
from .models import MaterialType, RecyclerPurchase, RecyclingCertificate

class MaterialTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaterialType
        fields = ['id', 'name', 'category', 'unit', 'base_price', 'description']

class RecyclerPurchaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecyclerPurchase
        fields = ['id', 'recycler', 'material_type', 'weight_kg', 'amount_paid', 'source_ward', 'purchase_date']
        read_only_fields = ['id', 'recycler', 'amount_paid', 'purchase_date']

class RecyclingCertificateSerializer(serializers.ModelSerializer):
    purchase_ids = serializers.ListField(
        child=serializers.PrimaryKeyRelatedField(queryset=RecyclerPurchase.objects.all()),
        write_only=True,
        required=False
    )
    
    class Meta:
        model = RecyclingCertificate
        fields = ['id', 'resident', 'recycler', 'certificate_number', 'status', 'certificate_file', 'purchases', 'purchase_ids', 'issued_at', 'metadata']
        read_only_fields = ['id', 'recycler', 'certificate_number', 'status', 'certificate_file', 'issued_at', 'purchases']
        extra_kwargs = {'resident': {'required': False, 'allow_null': True}}
