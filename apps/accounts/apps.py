from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.accounts'

    def ready(self):
        # Import spectacular extensions here to avoid circular imports in settings
        try:
            import greenloop.spectacular_extensions  # noqa
        except ImportError:
            pass
        
        # Monkey-patch drf-spectacular's GIS extension to fix KeyError: 'id'
        # This occurs during request schema generation for GeoFeatureModelSerializers
        try:
            from drf_spectacular.contrib.rest_framework_gis import GeoFeatureModelSerializerExtension
            
            original_map = GeoFeatureModelSerializerExtension.map_geo_feature_model_serializer
            
            def patched_map(self, serializer, base_schema):
                # Safe-guard against missing id_field in base_schema['properties']
                # (which happens for read_only fields in request schemas)
                id_field = getattr(serializer.Meta, 'id_field', None)
                if id_field and 'properties' in base_schema and id_field not in base_schema['properties']:
                    # Inject a dummy property to avoid KeyError during .pop()
                    base_schema['properties'][id_field] = {'type': 'string', 'readOnly': True}
                
                return original_map(self, serializer, base_schema)
            
            GeoFeatureModelSerializerExtension.map_geo_feature_model_serializer = patched_map
        except Exception:
            pass
