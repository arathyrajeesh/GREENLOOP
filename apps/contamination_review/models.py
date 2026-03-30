from django.db import models

class Pickup(models.Model):
    CLASSIFICATION_CHOICES = [
        ('clean', 'Clean'),
        ('contaminated', 'Contaminated'),
        ('mixed', 'Mixed'),
    ]

    image = models.ImageField(upload_to='pickups/review_images/')
    ai_classification = models.CharField(max_length=20, choices=CLASSIFICATION_CHOICES)
    confidence_score = models.FloatField()
    contamination_flag = models.BooleanField(default=False)
    needs_review = models.BooleanField(default=False)
    points_awarded = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Apply business logic automatically only on creation
        if self._state.adding and self.confidence_score is not None:
            if self.confidence_score >= 0.7 and self.ai_classification == 'contaminated':
                self.contamination_flag = True
                self.needs_review = True
            elif self.confidence_score < 0.7:
                self.needs_review = True
                
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Pickup {self.id} - {self.ai_classification} ({self.confidence_score})"
