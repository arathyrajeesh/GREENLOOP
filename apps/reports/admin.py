from django.contrib import admin
from .models import ReportCategory, Report, NPSSurvey

@admin.register(ReportCategory)
class ReportCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "description")
    search_fields = ("name",)

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "category", "is_public", "created_at")
    list_filter = ("category", "is_public", "created_at")
    search_fields = ("title", "content", "user__email")

@admin.register(NPSSurvey)
class NPSSurveyAdmin(admin.ModelAdmin):
    list_display = ("resident", "score", "category_label", "submitted_at", "next_prompt_at")
    list_filter = ("score", "submitted_at")
    search_fields = ("resident__name", "resident__email", "comment")
    readonly_fields = ("submitted_at",)

    def category_label(self, obj):
        return obj.category
    category_label.short_description = "Category"
