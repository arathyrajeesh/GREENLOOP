import factory
import random
import string
from django.contrib.gis.geos import Point, Polygon
from django.utils import timezone
from apps.users.models import User
from apps.wards.models import Ward
from apps.pickups.models import Pickup, PickupVerification
from apps.routes.models import Route
from apps.complaints.models import Complaint
from apps.accounts.models import OTPCode
from apps.dashboard.models import SyncQueue
from apps.attendance.models import AttendanceLog

class WardFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Ward

    name = factory.Faker('city')
    number = factory.Sequence(lambda n: n + 1)
    location = Point(76.9467, 8.5241)  # Trivandrum coords
    boundary = Polygon.from_bbox((76.9, 8.5, 77.0, 8.6))

class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    email = factory.Faker('email')
    name = factory.Faker('name')
    role = 'RESIDENT'
    is_active = True

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        password = extracted or 'password123'
        self.set_password(password)

class AdminFactory(UserFactory):
    role = 'ADMIN'
    is_staff = True
    is_superuser = True

class WorkerFactory(UserFactory):
    role = 'HKS_WORKER'
    username = factory.Sequence(lambda n: f"worker_{n}")
    ward = factory.SubFactory(WardFactory)

class ResidentFactory(UserFactory):
    role = 'RESIDENT'
    ward = factory.SubFactory(WardFactory)

class PickupFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Pickup

    resident = factory.SubFactory(ResidentFactory)
    ward = factory.SelfAttribute('resident.ward')
    location = Point(76.947, 8.525)
    waste_type = 'dry'
    status = 'pending'
    scheduled_date = factory.Faker('date_this_month')
    time_slot = '10:00-12:00'

class RouteFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Route

    hks_worker = factory.SubFactory(WorkerFactory)
    ward = factory.SelfAttribute('hks_worker.ward')
    route_date = factory.LazyFunction(lambda: timezone.now().date())
    planned_path = factory.LazyFunction(lambda: Point(76.9, 8.5).buffer(0.01).boundary) # A simple loop
    actual_path = None

class ComplaintFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Complaint

    reporter = factory.SubFactory(ResidentFactory)
    category = 'PICKUP'
    priority = 2
    description = factory.Faker('paragraph')
    status = 'submitted'

class OTPCodeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = OTPCode

    user = factory.SubFactory(UserFactory)
    code = factory.LazyFunction(lambda: ''.join(random.choices(string.digits, k=6)))

class SyncQueueFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SyncQueue

    user = factory.SubFactory(UserFactory)
    model_name = 'Pickup'
    action = 'UPDATE'
    payload = factory.LazyFunction(lambda: {"status": "completed"})
    status = 'PENDING'

class AttendanceLogFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AttendanceLog

    worker = factory.SubFactory(WorkerFactory)
    date = factory.LazyFunction(lambda: timezone.now().date())
    check_in = factory.LazyFunction(lambda: timezone.now().time())
    check_in_location = Point(76.95, 8.55)
    ppe_photo_url = factory.Faker('image_url')
