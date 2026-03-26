"""
drf-spectacular extensions to properly document GeoDjango (GIS) fields.
This file must be imported at startup via SPECTACULAR_SETTINGS['EXTENSIONS_BLACKLIST'] or
via AppConfig.ready(). We wire it through DEFAULT_SCHEMA_CLASS override instead.
"""
from drf_spectacular.extensions import OpenApiSerializerFieldExtension
from drf_spectacular.plumbing import build_basic_type
from drf_spectacular.types import OpenApiTypes


class PointFieldExtension(OpenApiSerializerFieldExtension):
    """Maps PointField to a GeoJSON Point object in the API schema."""
    target_class = 'rest_framework_gis.fields.GeometryField'

    def map_serializer_field(self, auto_schema, direction):
        return {
            "type": "object",
            "description": "GeoJSON geometry",
            "example": {
                "type": "Point",
                "coordinates": [76.2711, 10.8505]
            }
        }


class GeoJsonGeometryExtension(OpenApiSerializerFieldExtension):
    """Maps GeoJSON geometry fields (Point, LineString, etc.) to object schema."""
    target_class = 'rest_framework_gis.fields.GeometrySerializerMethodField'

    def map_serializer_field(self, auto_schema, direction):
        return {
            "type": "object",
            "description": "GeoJSON geometry",
        }
