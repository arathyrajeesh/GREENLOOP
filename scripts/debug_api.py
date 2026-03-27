import os
import django
import sys

# Setup Django
sys.path.append('/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'greenloop.settings.development')
django.setup()

from apps.wards.models import Ward
from apps.pickups.models import Pickup
from apps.wards.serializers import WardSerializer
from apps.pickups.serializers import PickupSerializer

def debug():
    print("Testing Wards Serialization...")
    try:
        wards = Ward.objects.all()
        print(f"Count: {wards.count()}")
        for w in wards:
            print(f"  Ward {w.id}: {w.name}, Boundary: {w.boundary is not None}")
        serializer = WardSerializer(wards, many=True)
        data = serializer.data
        print(f"Success! Features Count: {len(data.get('features', []))}")
    except Exception as e:
        import traceback
        print(f"Wards Failed: {e}")
        traceback.print_exc()

    print("\nTesting Pickups Serialization...")
    try:
        pickups = Pickup.objects.all()
        print(f"Count: {pickups.count()}")
        for p in pickups:
            print(f"  Pickup {p.id}: Location: {p.location is not None}, Waste: {p.waste_type}")
        serializer = PickupSerializer(pickups, many=True)
        data = serializer.data
        print(f"Success! Features Count: {len(data.get('features', []))}")
    except Exception as e:
        import traceback
        print(f"Pickups Failed: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    debug()
