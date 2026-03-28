import uuid
import random
from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from django.contrib.gis.geos import Point, LineString
from apps.users.models import User
from apps.wards.models import Ward
from apps.routes.models import Route
from django.utils import timezone

class Command(BaseCommand):
    help = 'Seeds 500 users and initial spatial data for load testing.'

    def handle(self, *args, **options):
        self.stdout.write("Cleaning up existing load test data...")
        User.objects.filter(email__contains="@loadtest.com").delete()
        Ward.objects.filter(name="Load Test Ward").delete()

        self.stdout.write("Seeding data for load testing...")
        
        # 1. Create a Ward
        ward = Ward.objects.create(
            name="Load Test Ward",
            number=999,
            location=Point(76.9467, 8.4875),
            boundary=Point(76.9467, 8.4875).buffer(0.01)
        )

        password = make_password("password123")
        
        # 2. Create Residents
        residents = []
        for i in range(250):
            residents.append(User(
                id=uuid.uuid4(),
                email=f"resident_{i}@loadtest.com",
                username=f"resident_{i}",
                name=f"Resident {i}",
                role='RESIDENT',
                password=password,
                ward=ward,
                is_active=True
            ))
        User.objects.bulk_create(residents)
        self.stdout.write(f"Created 250 residents.")

        # 3. Create Workers
        workers = []
        for i in range(250):
            workers.append(User(
                id=uuid.uuid4(),
                email=f"worker_{i}@loadtest.com",
                username=f"worker_{i}",
                name=f"Worker {i}",
                role='HKS_WORKER',
                password=password,
                ward=ward,
                is_active=True
            ))
        created_workers = User.objects.bulk_create(workers)
        self.stdout.write(f"Created 250 workers.")

        # 4. Create Routes for Workers
        routes = []
        today = timezone.now().date()
        # Refresh workers from DB to get IDs correctly if bulk_create didn't return them properly in some DBs
        db_workers = User.objects.filter(email__contains="worker_")
        for worker in db_workers:
            line = LineString((76.94, 8.48), (76.95, 8.49))
            routes.append(Route(
                hks_worker=worker,
                ward=ward,
                route_date=today,
                planned_path=line
            ))
        Route.objects.bulk_create(routes)
        self.stdout.write(f"Created 250 routes.")

        self.stdout.write(self.style.SUCCESS("Load test data seeding complete."))
