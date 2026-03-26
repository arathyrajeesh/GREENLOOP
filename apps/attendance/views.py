from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils import timezone
from django.contrib.gis.geos import Point
from .models import AttendanceLog
from .serializers import AttendanceLogSerializer
from drf_spectacular.utils import extend_schema

class AttendanceLogViewSet(viewsets.ModelViewSet):
    queryset = AttendanceLog.objects.all()
    serializer_class = AttendanceLogSerializer
    permission_classes = [permissions.IsAuthenticated]

class WorkerAttendanceView(APIView):
    """
    Logs attendance for an HKS Worker securely using GPS boundary validation 
    and PPE verification.
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(responses={201: AttendanceLogSerializer})
    def post(self, request):
        user = request.user
        if getattr(user, 'role', '') != 'HKS_WORKER':
            return Response({"error": "Only HKS Workers can log attendance here"}, status=status.HTTP_403_FORBIDDEN)
            
        # Parse Location
        loc_data = request.data.get('check_in_location')
        if not loc_data or 'coordinates' not in loc_data:
            return Response({"error": "check_in_location (GeoJSON Point format) is required"}, status=status.HTTP_400_BAD_REQUEST)
            
        coords = loc_data['coordinates']
        try:
            check_in_point = Point(coords[0], coords[1])
        except Exception:
            return Response({"error": "Invalid coordinates"}, status=status.HTTP_400_BAD_REQUEST)
        
        ward = user.ward
        if not ward:
            return Response({"error": "Worker does not have an assigned ward"}, status=status.HTTP_400_BAD_REQUEST)
            
        # GeoDjango Spatial Verification (ST_Within equivalent)
        if not ward.boundary.contains(check_in_point):
            return Response({"error": "Check-in Location is outside the assigned ward boundary"}, status=status.HTTP_400_BAD_REQUEST)
            
        # Enforce uniqueness per day
        today = timezone.now().date()
        if AttendanceLog.objects.filter(worker=user, date=today).exists():
            return Response({"error": "Attendance already logged for today"}, status=status.HTTP_400_BAD_REQUEST)
            
        log = AttendanceLog.objects.create(
            worker=user,
            date=today,
            check_in=timezone.now().time(),
            check_in_location=check_in_point,
            ppe_photo_url=request.data.get('ppe_photo_url'),
            has_gloves=str(request.data.get('has_gloves', 'False')).lower() == 'true',
            has_mask=str(request.data.get('has_mask', 'False')).lower() == 'true',
            has_vest=str(request.data.get('has_vest', 'False')).lower() == 'true',
            has_boots=str(request.data.get('has_boots', 'False')).lower() == 'true'
        )
        
        return Response(AttendanceLogSerializer(log).data, status=status.HTTP_201_CREATED)
