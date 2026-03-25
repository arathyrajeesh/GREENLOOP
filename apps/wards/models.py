from django.contrib.gis.db import models

class Ward(models.Model):
    name = models.CharField(max_length=100)
    number = models.PositiveIntegerField(unique=True)
    location = models.PointField(help_text="Centroid of the ward")
    boundary = models.MultiPolygonField(help_text="Geographical boundary of the ward")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Ward {self.number}: {self.name}"

    class Meta:
        verbose_name_plural = "Wards"
        ordering = ['number']
