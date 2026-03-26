from rest_framework import viewsets, permissions
from .models import MaterialType, RecyclerPurchase, RecyclingCertificate
from .serializers import MaterialTypeSerializer, RecyclerPurchaseSerializer, RecyclingCertificateSerializer

class MaterialTypeViewSet(viewsets.ModelViewSet):
    queryset = MaterialType.objects.all()
    serializer_class = MaterialTypeSerializer
    permission_classes = [permissions.IsAuthenticated]

class RecyclerPurchaseViewSet(viewsets.ModelViewSet):
    serializer_class = RecyclerPurchaseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return RecyclerPurchase.objects.none()
        user = self.request.user
        if user.role == 'RECYCLER':
            return RecyclerPurchase.objects.filter(recycler=user)
        return RecyclerPurchase.objects.all()

    def perform_create(self, serializer):
        material = serializer.validated_data['material_type']
        quantity = serializer.validated_data['quantity']
        total_price = material.price_per_unit * quantity
        serializer.save(recycler=self.request.user, total_price=total_price)

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

    def perform_create(self, serializer):
        import uuid
        cert_number = f"CERT-{uuid.uuid4().hex[:8].upper()}"
        serializer.save(recycler=self.request.user, certificate_number=cert_number)
