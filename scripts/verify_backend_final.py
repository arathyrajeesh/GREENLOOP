import asyncio
import websockets
import json
import os
import django
import sys

# Setup Django
sys.path.append('/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'greenloop.settings.development')
django.setup()

from apps.users.models import User
from rest_framework_simplejwt.tokens import RefreshToken

def verify_apis():
    print("--- 1. API Verification ---")
    from apps.wards.models import Ward
    from apps.pickups.models import Pickup
    from apps.wards.serializers import WardSerializer
    from apps.pickups.serializers import PickupSerializer

    wards = Ward.objects.all()
    w_serializer = WardSerializer(wards, many=True)
    print(f"Wards GeoJSON Features: {len(w_serializer.data.get('features', []))}")

    pickups = Pickup.objects.all()
    p_serializer = PickupSerializer(pickups, many=True)
    print(f"Pickups GeoJSON Features: {len(p_serializer.data.get('features', []))}")

async def verify_ws():
    print("\n--- 2. WebSocket Verification ---")
    # We obtain user outside or via sync_to_async if needed, 
    # but let's just do it in a simple way for this script.
    from asgiref.sync import sync_to_async
    
    @sync_to_async
    def get_token():
        worker = User.objects.filter(role='HKS_WORKER').first()
        return str(RefreshToken.for_user(worker).access_token)
    
    token = await get_token()
    uri = f"ws://daphne:8001/ws/tracking/?token={token}"
    
    try:
        async with websockets.connect(uri) as ws:
            print("Connected to WebSocket.")
            print("Sending 'On Route' location...")
            await ws.send(json.dumps({'latitude': 10.51, 'longitude': 76.91}))
            # Add a small wait for broadcast
            await asyncio.sleep(1)
            print("WebSocket Test Done.")
    except Exception as e:
        print(f"WebSocket Fail: {e}")

if __name__ == "__main__":
    verify_apis()
    asyncio.run(verify_ws())
