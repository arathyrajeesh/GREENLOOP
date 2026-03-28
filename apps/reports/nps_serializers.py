from rest_framework import serializers
from django.core.validators import MinValueValidator, MaxValueValidator
from .models import NPSSurvey


class NPSSurveySubmitSerializer(serializers.ModelSerializer):
    score = serializers.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(10)]
    )

    class Meta:
        model = NPSSurvey
        fields = ["score", "comment"]


class NPSSurveyResponseSerializer(serializers.ModelSerializer):
    category = serializers.CharField(read_only=True)

    class Meta:
        model = NPSSurvey
        fields = ["score", "comment", "category", "submitted_at", "next_prompt_at"]


class NPSSummarySerializer(serializers.Serializer):
    """Read-only serializer for the admin NPS dashboard."""
    total_responses = serializers.IntegerField()
    nps_score = serializers.FloatField(help_text="Calculated NPS (-100 to +100)")
    promoters = serializers.IntegerField()
    passives = serializers.IntegerField()
    detractors = serializers.IntegerField()
    average_score = serializers.FloatField()
    recent_comments = serializers.ListField(child=serializers.DictField())
