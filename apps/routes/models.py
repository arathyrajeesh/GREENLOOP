from django.contrib.gis.db import models
from django.utils import timezone

class Route(models.Model):
    hks_worker = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="routes",
        limit_choices_to={'role': 'HKS_WORKER'}
    )
    ward = models.ForeignKey("wards.Ward", on_delete=models.CASCADE, related_name="routes")
    route_date = models.DateField(default=timezone.now)
    planned_path = models.LineStringField(help_text="Planned collection path")
    actual_path = models.LineStringField(null=True, blank=True, help_text="Actual GPS track")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['hks_worker', 'route_date'], name='route_worker_date_idx'),
        ]

    def get_deviation(self):
        """Returns the Hausdorff distance between planned and actual paths."""
        if not self.actual_path:
            return None
        return self.planned_path.hausdorff_distance(self.actual_path)

    def __str__(self):
        return f"Route for {self.hks_worker} on {self.route_date}"
