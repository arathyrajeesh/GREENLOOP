from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer
from apps.wards.models import Ward

class WardSerializer(GeoFeatureModelSerializer):
    class Meta:
        model = Ward
        geo_field = "boundary" # Use boundary as the primary geo_field for GeoJSON
        id_field = "id"
        fields = ['id', 'name', 'number', 'location', 'boundary', 'created_at']
        extra_kwargs = {
            'location': {'required': False}
        }

    def validate(self, attrs):
        # Automatically calculate centroid if location is not provided
        if 'location' not in attrs and 'boundary' in attrs:
            attrs['location'] = attrs['boundary'].centroid
        return attrs

class WardAssignWorkersSerializer(serializers.Serializer):
    worker_ids = serializers.ListField(
        child=serializers.UUIDField(),
        help_text="List of UUIDs of workers to assign to this ward."
    )
