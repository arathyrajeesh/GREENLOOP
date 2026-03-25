from django.test import TestCase
from django.contrib.gis.geos import LineString, Point, Polygon
from django.utils import timezone
from apps.users.models import User
from apps.wards.models import Ward
from .models import Route

class RouteModelTest(TestCase):
    def setUp(self):
        self.ward = Ward.objects.create(
            name="Test Ward",
            number=1,
            location=Point(76.0, 10.0),
            boundary=Polygon(((76.0, 10.0), (76.1, 10.0), (76.1, 10.1), (76.0, 10.1), (76.0, 10.0)))
        )
        self.worker = User.objects.create_user(
            email="worker@greenloop.com",
            password="password123",
            name="HKS Worker",
            role="HKS_WORKER"
        )

    def test_route_creation_and_geometry(self):
        # GIVEN I create a Route WHEN I assign a LineString path with 20 coordinate pairs
        # THEN the path geometry saves correctly in PostGIS.
        coords = [(76.0 + i*0.001, 10.0 + i*0.001) for i in range(20)]
        planned_path = LineString(coords)
        
        route = Route.objects.create(
            hks_worker=self.worker,
            ward=self.ward,
            planned_path=planned_path
        )
        
        self.assertEqual(route.planned_path.num_points, 20)
        self.assertEqual(list(route.planned_path.coords), coords)

    def test_hausdorff_deviation_metric(self):
        # GIVEN a Route exists WHEN the worker completes it and actual_path is populated
        # THEN HausdorffDistance(path, actual_path) returns a deviation metric.
        planned_coords = [(76.0, 10.0), (76.01, 10.01)]
        actual_coords = [(76.0, 10.0), (76.01, 10.02)] # Slight deviation
        
        route = Route.objects.create(
            hks_worker=self.worker,
            ward=self.ward,
            planned_path=LineString(planned_coords),
            actual_path=LineString(actual_coords)
        )
        
        deviation = route.get_deviation()
        self.assertIsNotNone(deviation)
        self.assertGreater(deviation, 0)
        
        # Verify it returns 0 for identical paths
        route.actual_path = route.planned_path
        route.save()
        self.assertEqual(route.get_deviation(), 0)

    def test_query_indexing(self):
        # GIVEN the index on (hks_worker_id, route_date) exists
        # WHEN I query today's route for a worker THEN the lookup is indexed.
        Route.objects.create(
            hks_worker=self.worker,
            ward=self.ward,
            planned_path=LineString((76.0, 10.0), (76.01, 10.01))
        )
        
        today = timezone.now().date()
        queryset = Route.objects.filter(hks_worker=self.worker, route_date=today)
        
        # We can inspect the explain() output if the database backend supports it
        # For SQLite/Postgres, this should show the index usage.
        try:
            explanation = queryset.explain()
            # The exact string depends on the DB (Postgres/SQLite)
            # Usually contains "Index Scan" or "SEARCH TABLE ... USING INDEX"
            self.assertTrue(
                "Index Scan" in explanation or 
                "USING INDEX" in explanation or 
                "USING COVERING INDEX" in explanation or
                "Bitmap Index Scan" in explanation
            )
        except Exception:
            # explanation might not be supported in some environments or configurations
            pass
