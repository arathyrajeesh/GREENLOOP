from rest_framework_gis.serializers import GeoFeatureModelSerializer
from .models import Complaint

class ComplaintSerializer(GeoFeatureModelSerializer):
    class Meta:
        model = Complaint
        geo_field = "location"
        id_field = "id"
        fields = '__all__'
        read_only_fields = ['id', 'reporter', 'status', 'created_at', 'updated_at', 'resolved_at']
