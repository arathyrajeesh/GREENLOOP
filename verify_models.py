import os
import django
from django.db.models import Sum
from django.utils import timezone

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'greenloop.settings.development')
django.setup()

from apps.users.models import User
from apps.rewards.models import Reward
from apps.payments.models import FeeCollection
from apps.wards.models import Ward
from django.contrib.gis.geos import Point, Polygon

def verify_reward_balance():
    print("Verifying Reward Balance Aggregation...")
    user = User.objects.create_user(email="test_reward@example.com", name="Test User", role="RESIDENT")
    
    Reward.objects.create(resident=user, points=100, transaction_type="EARNED", description="First earn")
    Reward.objects.create(resident=user, points=50, transaction_type="EARNED", description="Second earn")
    Reward.objects.create(resident=user, points=-30, transaction_type="REDEEMED", description="First redeem")
    
    balance = Reward.objects.filter(resident=user).aggregate(total=Sum('points'))['total']
    print(f"Calculated Balance: {balance}")
    assert balance == 120, f"Expected 120, got {balance}"
    print("Reward balance verification passed!")

def verify_fee_receipt():
    print("\nVerifying FeeCollection Receipt Generation...")
    ward = Ward.objects.create(name="Test Ward", number=99, location=Point(0,0), boundary=Polygon(((0,0), (0,1), (1,1), (1,0), (0,0))))
    user = User.objects.create_user(email="test_fee@example.com", name="Fee User", role="RESIDENT")
    
    fee1 = FeeCollection.objects.create(resident=user, amount=500.00, payment_method="CASH")
    print(f"Fee 1 Receipt: {fee1.receipt_number}")
    assert fee1.receipt_number.startswith("FC-"), "Receipt should start with FC-"
    
    fee2 = FeeCollection.objects.create(resident=user, amount=200.00, payment_method="UPI")
    print(f"Fee 2 Receipt: {fee2.receipt_number}")
    
    # Check sequential numbering (assuming same day)
    num1 = int(fee1.receipt_number.split('-')[-1])
    num2 = int(fee2.receipt_number.split('-')[-1])
    assert num2 == num1 + 1, f"Sequential numbering failed: {num1} -> {num2}"
    print("FeeCollection receipt verification passed!")

if __name__ == "__main__":
    try:
        verify_reward_balance()
        verify_fee_receipt()
        print("\nAll model verifications passed successfully!")
    except Exception as e:
        print(f"\nVerification FAILED: {e}")
        exit(1)
