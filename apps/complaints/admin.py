from django.contrib.gis import admin
from .models import Complaint

@admin.register(Complaint)
class ComplaintAdmin(admin.GISModelAdmin):
    list_display = ("id", "reporter", "category", "status", "created_at")
    list_filter = ("status", "category", "created_at")
    search_fields = ("reporter__email", "reporter__name", "description")
    readonly_fields = ("created_at", "updated_at")
