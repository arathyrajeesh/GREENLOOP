from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer
from .models import Complaint

class ComplaintSerializer(GeoFeatureModelSerializer):
    class Meta:
        model = Complaint
        geo_field = "location"
        id_field = "id"
        fields = [
            'id', 'reporter', 'category', 'priority', 'description', 
            'location', 'image', 'assigned_to', 'status', 
            'is_escalated', 'resolved_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'reporter', 'status', 'is_escalated', 'created_at', 'updated_at', 'resolved_at']

class ComplaintHeatmapSerializer(serializers.Serializer):
    cluster_id = serializers.IntegerField()
    point_count = serializers.IntegerField()
    # Centroid of the cluster
    longitude = serializers.FloatField()
    latitude = serializers.FloatField()
