from rest_framework_gis.serializers import GeoFeatureModelSerializer
from apps.wards.models import Ward

class WardSerializer(GeoFeatureModelSerializer):
    class Meta:
        model = Ward
        geo_field = "boundary" # Use boundary as the primary geo_field for GeoJSON
        id_field = "id"
        fields = ['id', 'name', 'number', 'location', 'boundary', 'created_at']
