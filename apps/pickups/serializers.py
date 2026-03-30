from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer
from apps.pickups.models import Pickup, PickupSlot

class PickupSlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = PickupSlot
        fields = ['id', 'time_range', 'label', 'capacity', 'is_active']

class PickupSerializer(GeoFeatureModelSerializer):
    time_slot_details = PickupSlotSerializer(source='time_slot_ref', read_only=True)
    
    class Meta:
        model = Pickup
        geo_field = "location"
        id_field = "id"
        fields = [
            'id', 'resident', 'ward', 'waste_type', 
            'status', 'scheduled_date', 'time_slot_ref', 'time_slot', 'time_slot_details',
            'qr_code', 'completed_at', 'created_at'
        ]
        read_only_fields = ['resident', 'status', 'qr_code', 'completed_at', 'created_at']
        extra_kwargs = {
            'ward': {'required': False}
        }
