import json
from django.core.management.base import BaseCommand
from django.contrib.gis.geos import GEOSGeometry
from apps.wards.models import Ward

class Command(BaseCommand):
    help = "Seed wards from a GeoJSON file"

    def add_arguments(self, parser):
        parser.add_argument("file_path", type=str, help="Path to the GeoJSON file")

    def handle(self, *args, **options):
        file_path = options["file_path"]
        try:
            with open(file_path, "r") as f:
                data = json.load(f)

            for feature in data["features"]:
                props = feature["properties"]
                geom = GEOSGeometry(json.dumps(feature["geometry"]))
                
                # Centroid can be a list or a dict
                centroid = props["centroid"]
                if isinstance(centroid, list):
                    location = GEOSGeometry(f"POINT({centroid[0]} {centroid[1]})")
                else:
                    location = GEOSGeometry(json.dumps(centroid))

                Ward.objects.update_or_create(
                    number=props["number"],
                    defaults={
                        "name": props["name"],
                        "location": location,
                        "boundary": geom,
                    }
                )
            self.stdout.write(self.style.SUCCESS(f"Successfully seeded wards from {file_path}"))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error seeding wards: {str(e)}"))
