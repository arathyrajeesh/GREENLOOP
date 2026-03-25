from rest_framework import viewsets, permissions
from .models import MaterialType, RecyclerPurchase, RecyclingCertificate
from .serializers import MaterialTypeSerializer, RecyclerPurchaseSerializer, RecyclingCertificateSerializer

class MaterialTypeViewSet(viewsets.ModelViewSet):
    queryset = MaterialType.objects.all()
    serializer_class = MaterialTypeSerializer
    permission_classes = [permissions.IsAuthenticated]

class RecyclerPurchaseViewSet(viewsets.ModelViewSet):
    queryset = RecyclerPurchase.objects.all()
    serializer_class = RecyclerPurchaseSerializer
    permission_classes = [permissions.IsAuthenticated]

class RecyclingCertificateViewSet(viewsets.ModelViewSet):
    serializer_class = RecyclingCertificateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return RecyclingCertificate.objects.none()
            
        user = self.request.user
        if not user or user.is_anonymous:
            return RecyclingCertificate.objects.none()
            
        if user.role == 'RESIDENT':
            return RecyclingCertificate.objects.filter(resident=user)
        elif user.role == 'RECYCLER':
            return RecyclingCertificate.objects.filter(recycler=user)
        return RecyclingCertificate.objects.all()
