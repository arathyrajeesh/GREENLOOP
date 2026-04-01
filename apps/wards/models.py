from django.contrib.gis.db import models
from django.contrib.postgres.indexes import GistIndex

class Ward(models.Model):
    name = models.CharField(max_length=100)
    number = models.PositiveIntegerField(unique=True)
    location = models.PointField(help_text="Centroid of the ward")
    boundary = models.PolygonField(help_text="Geographical boundary of the ward")
    total_households = models.PositiveIntegerField(default=100, help_text="Total estimated households in this ward for coverage metrics")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Ward {self.number}: {self.name}"

    class Meta:
        verbose_name_plural = "Wards"
        ordering = ['number']
        indexes = [
            GistIndex(fields=['boundary']),
        ]
