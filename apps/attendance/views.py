from rest_framework import viewsets, permissions
from .models import AttendanceLog
from .serializers import AttendanceLogSerializer

class AttendanceLogViewSet(viewsets.ModelViewSet):
    queryset = AttendanceLog.objects.all()
    serializer_class = AttendanceLogSerializer
    permission_classes = [permissions.IsAuthenticated]
