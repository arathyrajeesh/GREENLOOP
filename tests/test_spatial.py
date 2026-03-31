import pytest
from django.contrib.gis.geos import Point, Polygon
from tests.factories import WardFactory, PickupFactory

@pytest.mark.django_db
class TestSpatialQueries:
    """
    Tests geographic operations (ST_Within, ST_Distance).
    Note: Requires PostGIS or SpatiaLite in production/test DB.
    Since we are in PostGIS, these should work.
    """
    
    def test_pickup_in_ward_boundary(self, db):
        # A ward centered at (76.9, 8.5) with 0.1 deg width
        ward = WardFactory(
            boundary=Polygon.from_bbox((76.8, 8.4, 77.0, 8.6))
        )
        
        # Inside
        p1 = PickupFactory(location=Point(76.9, 8.5), resident__ward=ward)
        # Outside
        p2 = PickupFactory(location=Point(80.0, 10.0), resident__ward=ward)
        
        from apps.pickups.models import Pickup
        inside_ward = Pickup.objects.filter(location__within=ward.boundary)
        
        assert p1 in inside_ward
        assert p2 not in inside_ward

    def test_distance_calculation(self, db):
        # Calculate distance between two points
        # 1 degree is roughly 111km at equator
        p1 = Point(0, 0)
        p2 = Point(1, 0)
        
        # In GeoDjango distance is a Distance object
        from django.contrib.gis.db.models.functions import Distance
        from apps.awards.models import Ward # Use any model for query
        # Since I don't have a simple way to test distance without a model, 
        # let's use Ward.
        w1 = WardFactory(location=p1)
        
        with_distance = Ward.objects.annotate(dist=Distance('location', p2)).get(id=w1.id)
        # Check that it's close to 1 degree
        assert 0.9 <= with_distance.dist.value <= 1.1 
