from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer
from apps.pickups.models import Pickup, PickupSlot

class PickupSlotSerializer(serializers.ModelSerializer):
    # Enforce non-null strings and ints to prevent Flutter "Null is not a subtype of String" crashes
    time_range = serializers.CharField(default="00:00 - 00:00", allow_null=False)
    label = serializers.CharField(default="Time Slot", allow_null=False)
    capacity = serializers.IntegerField(default=15, allow_null=False)
    is_active = serializers.BooleanField(default=True, allow_null=False)

    class Meta:
        model = PickupSlot
        fields = ['id', 'time_range', 'label', 'capacity', 'is_active']

class PickupSerializer(GeoFeatureModelSerializer):
    time_slot_details = PickupSlotSerializer(source='time_slot_ref', read_only=True)
    # Ensure time_slot is never null in output to prevent Flutter crashes
    time_slot = serializers.CharField(default="", allow_null=False, required=False)

    def validate_waste_type(self, value):
        """
        Normalize waste_type to lowercase before saving.
        This fixes the issue where some frontends send "DRY" instead of "dry".
        """
        if value:
            return value.lower()
        return value
    
    class Meta:
        model = Pickup
        geo_field = "location"
        id_field = "id"
        fields = [
            'id', 'resident', 'ward', 'waste_type', 
            'status', 'scheduled_date', 'is_instant', 'time_slot_ref', 'time_slot', 'time_slot_details',
            'qr_code', 'completed_at', 'created_at'
        ]
        read_only_fields = ['resident', 'status', 'qr_code', 'completed_at', 'created_at']
        extra_kwargs = {
            'ward': {'required': False}
        }
