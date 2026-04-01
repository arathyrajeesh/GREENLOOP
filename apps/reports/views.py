from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from apps.users.permissions import IsAdminUser
from .models import ReportCategory, Report, WardCollectionReport
from .serializers import ReportCategorySerializer, ReportSerializer, WardCollectionReportSerializer
from .tasks import generate_ward_collection_report, generate_suchitwa_mission_report

class ReportCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ReportCategory.objects.all()
    serializer_class = ReportCategorySerializer
    permission_classes = [permissions.AllowAny]

class ReportViewSet(viewsets.ModelViewSet):
    serializer_class = ReportSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        if self.request.user.is_staff:
            return Report.objects.all()
        return Report.objects.filter(is_public=True)

class WardCollectionReportViewSet(viewsets.ModelViewSet):
    serializer_class = WardCollectionReportSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    
    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return WardCollectionReport.objects.none()
        return WardCollectionReport.objects.all()
        
    def perform_create(self, serializer):
        report = serializer.save(generated_by=self.request.user, status='PENDING')
        
        # Trigger the specific task based on report_type
        if report.report_type == 'COMPLIANCE':
            generate_suchitwa_mission_report.delay(report.id)
        else:
            # Default to general ward report for now for WARD, PERFORMANCE, FINANCIAL
            generate_ward_collection_report.delay(report.id)

