from rest_framework import viewsets, permissions
from .models import OTPCode
from .serializers import OTPCodeSerializer

class OTPCodeViewSet(viewsets.ModelViewSet):
    queryset = OTPCode.objects.all()
    serializer_class = OTPCodeSerializer
    permission_classes = [permissions.IsAuthenticated]
