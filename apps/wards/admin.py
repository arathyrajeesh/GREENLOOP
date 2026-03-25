from django.contrib.gis import admin
from .models import Ward

@admin.register(Ward)
class WardAdmin(admin.GISModelAdmin):
    list_display = ("number", "name", "created_at")
    search_fields = ("name", "number")
    ordering = ("number",)
