from rest_framework_gis.serializers import GeoFeatureModelSerializer
from .models import Complaint

class ComplaintSerializer(GeoFeatureModelSerializer):
    class Meta:
        model = Complaint
        geo_field = "location"
        id_field = "id"
        fields = '__all__'
