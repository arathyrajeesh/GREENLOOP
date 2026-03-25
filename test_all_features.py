import os
import django
import uuid
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'greenloop.settings')
django.setup()

from apps.users.models import User
from apps.wards.models import Ward
from apps.pickups.models import Pickup
from apps.rewards.models import Reward
from apps.payments.models import FeeCollection
from django.contrib.gis.geos import Point
from django.db.models import Sum

def test_qr_generation():
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
    assert len(pickup.qr_code) == 64  # SHA-256 is 64 chars
    print(f"SUCCESS: Generated QR hash: {pickup.qr_code[:10]}...")

def test_reward_aggregation():
    print("Testing Reward Point Aggregation...")
    user = User.objects.get(email="test_resident@example.com")
    Reward.objects.create(resident=user, points=50, description="Earned 50", transaction_type="EARNED")
    Reward.objects.create(resident=user, points=-10, description="Spent 10", transaction_type="REDEEMED")
    
    total = Reward.objects.filter(resident=user).aggregate(Sum('points'))['points__sum']
    assert total == 40
    print(f"SUCCESS: Total points for resident: {total}")

def test_fee_collection_receipt():
    print("Testing Fee Collection Receipt Generation...")
    user = User.objects.get(email="test_resident@example.com")
    ward = Ward.objects.get(number=101)
    fee = FeeCollection.objects.create(
        resident=user,
        ward=ward,
        amount=Decimal("150.00"),
        payment_mode="CASH"
    )
    assert fee.receipt_number.startswith("FC-")
    print(f"SUCCESS: Generated Receipt: {fee.receipt_number}")

if __name__ == "__main__":
    try:
        test_qr_generation()
        test_reward_aggregation()
        test_fee_collection_receipt()
        print("\nALL SYSTEM TESTS PASSED!")
    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        exit(1)
