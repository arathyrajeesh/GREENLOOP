from rest_framework_gis.serializers import GeoFeatureModelSerializer
from .models import AttendanceLog

class AttendanceLogSerializer(GeoFeatureModelSerializer):
    class Meta:
        model = AttendanceLog
        geo_field = 'check_in_location'
        fields = '__all__'
