import os
import django
import pytest
from decimal import Decimal
from django.contrib.gis.geos import Point
from django.db.models import Sum

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'greenloop.settings')
django.setup()

from apps.users.models import User
from apps.wards.models import Ward
from apps.pickups.models import Pickup
from apps.rewards.models import Reward
from apps.payments.models import FeeCollection

@pytest.mark.django_db
def test_all_features():
    """All-in-one feature test to handle database isolation in pytest-django"""
    
    # 1. QR Generation
    print("Testing QR Code Generation...")
    user, _ = User.objects.get_or_create(email="test_resident@example.com", defaults={"name": "Test Resident", "role": "RESIDENT"})
    ward, _ = Ward.objects.get_or_create(
        number=101, 
        defaults={
            "name": "Verification Ward",
            "location": Point(70.0, 22.0),
            "boundary": "POLYGON((69 21, 69 23, 71 23, 71 21, 69 21))"
        }
    )
    pickup = Pickup.objects.create(
        resident=user,
        ward=ward,
        location=Point(70.0, 22.0),
        waste_type="dry",
        status="pending"
    )
    assert pickup.qr_code is not None
    assert len(pickup.qr_code) == 64
    print(f"SUCCESS: Generated QR hash: {pickup.qr_code[:10]}...")

    # 2. Reward aggregation
    print("Testing Reward Point Aggregation...")
    Reward.objects.create(resident=user, points=50, description="Earned 50", transaction_type="EARNED")
    Reward.objects.create(resident=user, points=-10, description="Spent 10", transaction_type="REDEEMED")
    
    total = Reward.objects.filter(resident=user).aggregate(Sum('points'))['points__sum']
    assert total == 40
    print(f"SUCCESS: Total points for resident: {total}")

    # 3. Fee Collection Receipt
    print("Testing Fee Collection Receipt Generation...")
    fee = FeeCollection.objects.create(
        resident=user,
        ward=ward,
        amount=Decimal("150.00"),
        payment_method="CASH"
    )
    assert fee.receipt_number.startswith("FC-")
    print(f"SUCCESS: Generated Receipt: {fee.receipt_number}")
