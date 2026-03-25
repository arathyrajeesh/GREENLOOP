from django.contrib.gis import admin
from .models import Route

@admin.register(Route)
class RouteAdmin(admin.GISModelAdmin):
    list_display = ('hks_worker', 'ward', 'route_date', 'created_at')
    list_filter = ('route_date', 'ward', 'hks_worker')
    search_fields = ('hks_worker__email', 'hks_worker__name', 'ward__name')
