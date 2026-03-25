from rest_framework_gis.serializers import GeoFeatureModelSerializer
from apps.pickups.models import Pickup

class PickupSerializer(GeoFeatureModelSerializer):
    class Meta:
        model = Pickup
        geo_field = "location"
        fields = [
            'id', 'resident', 'ward', 'waste_type', 
            'status', 'scheduled_date', 'qr_code', 
            'completed_at', 'created_at'
        ]
        read_only_fields = ['qr_code', 'completed_at', 'created_at']
