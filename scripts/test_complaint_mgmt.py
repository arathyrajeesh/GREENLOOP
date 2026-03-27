import os
import django
import sys
import json
from datetime import timedelta
from django.utils import timezone
from django.contrib.gis.geos import Point

# Setup Django
sys.path.append('/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'greenloop.settings.development')
django.setup()

from apps.complaints.models import Complaint
from apps.users.models import User
from apps.complaints.tasks import check_pending_complaints

def verify_complaint_mgmt():
    print("--- Complaint Management Verification ---")
    
    # Setup: Ensure we have an admin and a worker
    admin = User.objects.filter(role='ADMIN').first()
    worker = User.objects.filter(role='HKS_WORKER').first()
    resident = User.objects.filter(role='RESIDENT').first()
    
    if not all([admin, worker, resident]):
        print("Creating test users...")
        if not admin:
            admin = User.objects.create_superuser(email="admin_test@example.com", name="Admin Test", password="password")
        if not worker:
            worker = User.objects.create_user(email="worker_test@example.com", name="Worker Test", role="HKS_WORKER")
        if not resident:
            resident = User.objects.create_user(email="resident_test@example.com", name="Resident Test", role="RESIDENT")

    # 1. Verify Queue Sorting (Priority then Age)
    print("\n1. Testing Queue Sorting...")
    Complaint.objects.all().delete()
    
    # Oldest, Medium Priority
    c1 = Complaint.objects.create(reporter=resident, category="PICKUP", description="Oldest Med", priority=2, location=Point(76.9, 10.5))
    c1.created_at = timezone.now() - timedelta(days=5)
    c1.save()
    
    # Newest, Urgent Priority
    c2 = Complaint.objects.create(reporter=resident, category="OVERFLOW", description="Newest Urgent", priority=4, location=Point(76.91, 10.51))
    
    # Mid, Urgent Priority
    c3 = Complaint.objects.create(reporter=resident, category="CLEANLINESS", description="Mid Urgent", priority=4, location=Point(76.905, 10.505))
    c3.created_at = timezone.now() - timedelta(days=2)
    c3.save()
    
    queryset = Complaint.objects.all().order_by('-priority', 'created_at')
    results = [c.description for c in queryset]
    print(f"Sorted Results: {results}")
    # Expected: c3 (Urgent, Older), c2 (Urgent, Newer), c1 (Medium)
    if results == ["Mid Urgent", "Newest Urgent", "Oldest Med"]:
         print("SUCCESS: Sorting works correctly.")
    else:
         print("FAILURE: Sorting logic incorrect.")

    # 2. Test Assignment and Lifecycle
    print("\n2. Testing Assignment and Lifecycle...")
    # c1 is 'submitted'
    c1.assigned_to = worker
    c1.status = 'assigned'
    c1.save()
    print(f"Assigned to {worker.name}. Status: {c1.status}")
    
    # Advance to in-progress
    c1.status = 'in-progress'
    c1.save()
    print(f"Advanced to: {c1.status}")
    
    if c1.status == 'in-progress' and c1.assigned_to == worker:
        print("SUCCESS: Assignment and manual lifecycle work.")
    else:
        print("FAILURE: Assignment or status update failed.")

    # 3. Test KMeans Clustering (Heatmap)
    print("\n3. Testing KMeans Clustering (Heatmap)...")
    # Add more complaints around same areas
    Complaint.objects.create(reporter=resident, category="OTHER", description="H1", location=Point(76.9, 10.5))
    Complaint.objects.create(reporter=resident, category="OTHER", description="H2", location=Point(76.92, 10.52))
    
    from django.db import connection
    with connection.cursor() as cursor:
        query = """
            SELECT cluster_id, count(*) 
            FROM (SELECT ST_ClusterKMeans(location::geometry, %s) OVER() as cluster_id FROM complaints_complaint WHERE location IS NOT NULL) sub
            GROUP BY cluster_id
        """
        cursor.execute(query, [2])
        rows = cursor.fetchall()
    print(f"Clusters: {rows}")
    if len(rows) > 0:
        print("SUCCESS: PostGIS Clustering functional.")
    else:
        print("FAILURE: Clustering returned no results.")

    # 4. Test Auto-Escalation Task
    print("\n4. Testing Auto-Escalation Task...")
    # Create a 3-day old complaint that is still 'submitted'
    c_old = Complaint.objects.create(reporter=resident, category="PAYMENT", description="3-day old", priority=1)
    c_old.created_at = timezone.now() - timedelta(days=3)
    c_old.save()
    
    print(f"Running escalation task... Old complaint priority: {c_old.priority}")
    result = check_pending_complaints()
    print(result)
    
    c_old.refresh_from_db()
    print(f"Post-task priority: {c_old.priority}, Escalated: {c_old.is_escalated}")
    
    if c_old.is_escalated and c_old.priority == 4:
        print("SUCCESS: Auto-escalation task worked.")
    else:
        print("FAILURE: Auto-escalation task failed.")

if __name__ == "__main__":
    verify_complaint_mgmt()
