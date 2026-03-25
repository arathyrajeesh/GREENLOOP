from rest_framework import serializers
from .models import SyncQueue

class SyncQueueSerializer(serializers.ModelSerializer):
    class Meta:
        model = SyncQueue
        fields = '__all__'
