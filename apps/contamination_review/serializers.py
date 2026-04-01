from rest_framework import serializers
from .models import Pickup

class ContaminationPickupSerializer(serializers.ModelSerializer):
    """
    Serializer for the Contamination Review System's Pickup model.
    Handles image uploads, AI classifications, and read-only logic flags.
    """
    class Meta:
        model = Pickup
        fields = [
            'id', 
            'image', 
            'ai_classification', 
            'confidence_score',
            'contamination_flag', 
            'needs_review', 
            'points_awarded', 
            'created_at'
        ]
        read_only_fields = ['contamination_flag', 'needs_review', 'created_at']

    def validate_ai_classification(self, value):
        """Ensure ai_classification is one of the allowed choices."""
        allowed_classifications = ['clean', 'contaminated', 'mixed']
        if value not in allowed_classifications:
            raise serializers.ValidationError(
                f"ai_classification must be one of: {', '.join(allowed_classifications)}"
            )
        return value

    def validate_confidence_score(self, value):
        """Ensure confidence_score is strictly between 0 and 1 inclusive."""
        if not (0.0 <= value <= 1.0):
            raise serializers.ValidationError("confidence_score must be between 0 and 1.")
        return value

    def create(self, validated_data):
        """
        Create a new Pickup instance. 
        The business logic for flags is automatically applied via the model's save() method.
        """
        # We explicitly create and save to ensure the model's overridden save() runs.
        instance = Pickup(**validated_data)
        instance.save()
        return instance
