from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer
from apps.routes.models import Route

class RouteSerializer(GeoFeatureModelSerializer):
    # This simplifies the line to keep ONLY the important turning points.
    actual_path_simple = serializers.SerializerMethodField()

    def get_actual_path_simple(self, obj):
        if not obj.actual_path:
            return None
        # Simplifies the line to a tolerance of 0.0001 degrees
        # (approximately 10 meters of detail).
        simple = obj.actual_path.simplify(0.0001, preserve_topology=True)
        from django.contrib.gis.serializers.geojson import Serializer as GeoJSONSerializer
        return eval(GeoJSONSerializer().serialize([simple], geometry_field='geom'))['features'][0]['geometry']

    class Meta:
        model = Route
        geo_field = "planned_path"
        id_field = "id"
        fields = [
            'id', 'hks_worker', 'ward', 'route_date', 
            'planned_path', 'actual_path', 'actual_path_simple', 'created_at'
        ]
        read_only_fields = ['created_at']
