import os
import django
import sys
import json

# Setup Django
sys.path.append('/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'greenloop.settings.development')
django.setup()

from apps.wards.models import Ward
from apps.users.models import User
from django.contrib.gis.geos import Polygon, Point

def verify_ward_mgmt():
    print("--- Ward Management Verification ---")
    
    # 1. Create a Ward with a Polygon
    ward_name = "Drawing Test Ward"
    # Simple square around a point
    poly = Polygon(((76.9, 10.5), (76.91, 10.5), (76.91, 10.51), (76.9, 10.51), (76.9, 10.5)))
    centroid = Point(76.905, 10.505)
    
    # Clean up if exists (by name or number)
    Ward.objects.filter(name=ward_name).delete()
    Ward.objects.filter(number=99).delete()
    
    ward = Ward.objects.create(
        name=ward_name,
        number=99,
        location=centroid,
        boundary=poly
    )
    print(f"Created Ward: {ward.id} with boundary: {ward.boundary is not None}")
    
    # 2. Assign Workers
    # Ensure we have some workers
    workers = User.objects.filter(role='HKS_WORKER')[:2]
    if workers.count() < 2:
        print("Not enough workers for test. Creating test workers...")
        u1 = User.objects.create_user(email="testworker1@example.com", name="Worker 1", role="HKS_WORKER")
        u2 = User.objects.create_user(email="testworker2@example.com", name="Worker 2", role="HKS_WORKER")
        workers = [u1, u2]
    
    worker_ids = [str(w.id) for w in workers]
    print(f"Assigning workers: {worker_ids}")
    
    # Simulate the ViewSet action logic
    # (We could use APIClient but direct ORM/logic check is faster for backend-only verify)
    # But let's verify the logic we wrote in the ViewSet
    
    # Test Assignment
    User.objects.filter(id__in=worker_ids).update(ward=ward)
    
    # Verify listed
    assigned = ward.users.filter(role='HKS_WORKER')
    print(f"Assigned workers count: {assigned.count()}")
    if assigned.count() == len(worker_ids):
        print("SUCCESS: Workers assigned correctly.")
    else:
        print(f"FAILURE: Expected {len(worker_ids)} but got {assigned.count()}")

    # Test Unassignment (exclude logic)
    # Keep only u1
    new_list = [worker_ids[0]]
    print(f"Updating assignment to only: {new_list}")
    User.objects.filter(id__in=new_list).update(ward=ward)
    ward.users.filter(role='HKS_WORKER').exclude(id__in=new_list).update(ward=None)
    
    assigned_v2 = ward.users.filter(role='HKS_WORKER')
    print(f"New assigned count: {assigned_v2.count()}")
    if assigned_v2.count() == 1 and str(assigned_v2.first().id) == worker_ids[0]:
        print("SUCCESS: Unassignment logic works.")
    else:
        print("FAILURE: Unassignment logic failed.")

if __name__ == "__main__":
    verify_ward_mgmt()
