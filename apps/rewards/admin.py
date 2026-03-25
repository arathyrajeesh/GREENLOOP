from django.contrib import admin
from .models import Reward, RewardRedemption

@admin.register(Reward)
class RewardAdmin(admin.ModelAdmin):
    list_display = ("resident", "points", "transaction_type", "created_at")
    list_filter = ("transaction_type", "created_at", "resident")
    search_fields = ("resident__email", "resident__name", "description")

@admin.register(RewardRedemption)
class RewardRedemptionAdmin(admin.ModelAdmin):
    list_display = ("resident", "reward_item", "points_spent", "status", "created_at")
    list_filter = ("status", "created_at", "resident")
    search_fields = ("resident__email", "resident__name", "reward_item")
