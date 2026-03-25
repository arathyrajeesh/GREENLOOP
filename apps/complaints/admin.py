from django.contrib.gis import admin
from .models import Complaint

@admin.register(Complaint)
class ComplaintAdmin(admin.GISModelAdmin):
    list_display = ("id", "resident", "category", "status", "created_at")
    list_filter = ("status", "category", "created_at")
    search_fields = ("resident__email", "resident__name", "description")
    readonly_fields = ("created_at", "updated_at")
