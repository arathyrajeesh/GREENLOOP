from rest_framework import status
from rest_framework.test import APITestCase
from apps.users.models import User
from apps.wards.models import Ward
from apps.pickups.models import Pickup
from django.urls import reverse
from django.contrib.gis.geos import Point

class ScratchInstantTest(APITestCase):
    def setUp(self):
        self.ward = Ward.objects.create(name="W1", number=1, location=Point(0,0), boundary=Point(0,0).buffer(1))
        self.user = User.objects.create(email="u1@test.com", role="RESIDENT", ward=self.ward)
        self.client.force_authenticate(user=self.user)
    
    def test_create_wet_instant(self):
        url = reverse('pickup-list')
        data = {
            "waste_type": "wet",
            "is_instant": True,
            "location": {"type": "Point", "coordinates": [0.0, 0.0]}
        }
        response = self.client.post(url, data, format='json')
        print(f"RESPONSE DATA: {response.data}")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['waste_type'], "wet")
        self.assertTrue(response.data['is_instant'])
