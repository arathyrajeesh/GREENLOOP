from django.contrib import admin
from .models import ReportCategory, Report

@admin.register(ReportCategory)
class ReportCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "description")
    search_fields = ("name",)

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "category", "is_public", "created_at")
    list_filter = ("category", "is_public", "created_at")
    search_fields = ("title", "content", "user__email")
