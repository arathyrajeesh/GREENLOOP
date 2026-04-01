from rest_framework import serializers
from .models import SyncQueue

class SyncQueueSerializer(serializers.ModelSerializer):
    class Meta:
        model = SyncQueue
        fields = '__all__'
        read_only_fields = ['id', 'user', 'created_at', 'synced_at', 'status', 'conflict_reason']

class DashboardStatsSerializer(serializers.Serializer):
    """
    Serializer for summarizing system-wide KPIs for the Admin Dashboard.
    """
    kpis = serializers.DictField(child=serializers.FloatField())
    weekly_trend = serializers.ListField(child=serializers.DictField())
    ward_comparison = serializers.ListField(child=serializers.DictField())
    nps_stats = serializers.DictField()
