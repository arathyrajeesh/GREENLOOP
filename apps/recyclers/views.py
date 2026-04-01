from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import MaterialType, RecyclerPurchase, RecyclingCertificate
from .serializers import MaterialTypeSerializer, RecyclerPurchaseSerializer, RecyclingCertificateSerializer
from apps.users.permissions import IsAdminUser, IsRecyclerUser
from .tasks import generate_recycling_certificate_pdf

@extend_schema(tags=['Recycler', 'Materials'])
class MaterialTypeViewSet(viewsets.ModelViewSet):
    queryset = MaterialType.objects.all()
    serializer_class = MaterialTypeSerializer
    permission_classes = [permissions.IsAuthenticated]

@extend_schema(tags=['Recycler', 'Purchases'])
class RecyclerPurchaseViewSet(viewsets.ModelViewSet):
    serializer_class = RecyclerPurchaseSerializer
    permission_classes = [permissions.IsAuthenticated, IsRecyclerUser]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return RecyclerPurchase.objects.none()
        user = self.request.user
        if user.role == 'RECYCLER':
            return RecyclerPurchase.objects.filter(recycler=user)
        return RecyclerPurchase.objects.all()

    def perform_create(self, serializer):
        material = serializer.validated_data['material_type']
        weight_kg = serializer.validated_data['weight_kg']
        # Use base_price from MaterialType if amount_paid isn't provided (already handled in models but good to be explicit)
        amount_paid = material.base_price * weight_kg
        serializer.save(recycler=self.request.user, amount_paid=amount_paid)

@extend_schema(tags=['Recycler', 'Certificates'])
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
        purchase_ids = serializer.validated_data.pop('purchase_ids', [])
        cert_number = f"CERT-{uuid.uuid4().hex[:8].upper()}"
        
        # Ensure only recycler role can request new certificates
        if self.request.user.role != 'RECYCLER':
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only recyclers can request certificates.")
            
        certificate = serializer.save(
            recycler=self.request.user, 
            certificate_number=cert_number,
            status='PENDING'
        )
        
        if purchase_ids:
            certificate.purchases.set(purchase_ids)
            
        # Trigger background PDF generation task
        generate_recycling_certificate_pdf.delay(certificate.id)

    @extend_schema(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated, IsAdminUser], tags=['Admin', 'Certificates'])
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated, IsAdminUser])
    def verify(self, request, pk=None):
        """
        Admin only: Verifies the certificate and notifies the recycler.
        """
        certificate = self.get_object()
        certificate.status = 'VERIFIED'
        certificate.save()
        
        # Trigger notification
        from apps.notifications.tasks import notify_recycler_certificate_verified
        notify_recycler_certificate_verified.delay(certificate.id)
        
        return Response({"status": "verified", "message": "Certificate verified and recycler notified."})

    @extend_schema(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated, IsAdminUser], tags=['Admin', 'Certificates'])
    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated, IsAdminUser])
    def admin_pending(self, request):
        """
        Admin only: Lists all pending certificates requiring review.
        """
        queryset = RecyclingCertificate.objects.filter(status='PENDING')
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
