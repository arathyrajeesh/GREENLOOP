from rest_framework_gis.serializers import GeoFeatureModelSerializer
from apps.routes.models import Route

class RouteSerializer(GeoFeatureModelSerializer):
    class Meta:
        model = Route
        geo_field = "planned_path"
        fields = [
            'id', 'hks_worker', 'ward', 'route_date', 
            'planned_path', 'actual_path', 'created_at'
        ]
        read_only_fields = ['created_at']
