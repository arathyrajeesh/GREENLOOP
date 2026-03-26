import random
import string
from rest_framework import viewsets, permissions, views, status, response, serializers
from rest_framework_simplejwt.tokens import RefreshToken
from django.conf import settings
from apps.users.models import User
from django.core.mail import send_mail
from drf_spectacular.utils import extend_schema
from .models import OTPCode
from django.core.management import call_command
from .serializers import (
    OTPCodeSerializer, 
    OTPRequestSerializer, 
    OTPVerifySerializer,
    BaseResponseSerializer
)

class OTPCodeViewSet(viewsets.ModelViewSet):
    queryset = OTPCode.objects.all()
    serializer_class = OTPCodeSerializer
    permission_classes = [permissions.IsAuthenticated]

class PingView(views.APIView):
    """
    Diagnostic view to check database and model health in production.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        try:
            user_count = User.objects.count()
            otp_count = OTPCode.objects.count()
            return response.Response({
                "status": "ok",
                "database": "connected",
                "user_count": user_count,
                "otp_count": otp_count,
                "environment": "production" if not settings.DEBUG else "development"
            })
        except Exception as e:
            return response.Response({
                "status": "error",
                "message": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class MigrateView(views.APIView):
    """
    Emergency view to trigger migrations manually if entrypoint.sh is bypassed.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        try:
            # Trigger migrate command
            call_command('migrate', interactive=False)
            return response.Response({
                "status": "success",
                "message": "Migrations applied successfully."
            })
        except Exception as e:
            return response.Response({
                "status": "error",
                "message": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class OTPRequestView(views.APIView):
    permission_classes = [permissions.AllowAny]
    throttle_scope = 'otp_request'

    @extend_schema(
        request=OTPRequestSerializer, 
        responses={200: BaseResponseSerializer}
    )
    def post(self, request):
        email = request.data.get('email')
        if not email:
            return response.Response({"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get or create resident user
        user = User.objects.filter(email=email).first()

        if not user:
            user = User.objects.create_user(
                email=email,
                password=None,
                name=email.split('@')[0],
                role='RESIDENT'
            )
            created = True
        else:
            created = False
        
        # Generate 6-digit OTP
        otp_code = ''.join(random.choices(string.digits, k=6))
        OTPCode.objects.create(user=user, code=otp_code)
        
        # Send actual SMTP email
        subject = "GreenLoop Login OTP"
        message = f"Your GreenLoop login OTP is {otp_code}. It is valid for 5 minutes."
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@greenloop.com')
        try:
            send_mail(
                subject, 
                message, 
                from_email, 
                [email],
                fail_silently=False  # Changed to False to catch the exact error in logs
            )
        except Exception as e:
            # Important: Log the error for Render logs
            print(f"SMTP ERROR for {email}: {str(e)}")
            # For now, let's include the error in the response if DEBUG is on or for testing
            if settings.DEBUG:
                return response.Response({"error": f"Email failure: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return response.Response({
            "message": "OTP sent successfully",
            "is_new_user": created
        }, status=status.HTTP_200_OK)

class OTPVerifyView(views.APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        request=OTPVerifySerializer, 
        responses={200: BaseResponseSerializer}
    )
    def post(self, request):
        email = request.data.get('email')
        code = request.data.get('code')
        
        if not email or not code:
            return response.Response({"error": "Email and code are required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(email=email)
            otp = OTPCode.objects.filter(user=user, is_used=False).first()
            
            if not otp:
                 return response.Response({"error": "No OTP found"}, status=status.HTTP_404_NOT_FOUND)

            if not otp.is_valid():
                 return response.Response({"error": "OTP expired or too many attempts"}, status=status.HTTP_400_BAD_REQUEST)

            if otp.code == code:
                otp.is_used = True
                otp.save()
                
                # Generate JWT tokens with custom claims
                refresh = RefreshToken.for_user(user)
                refresh['role'] = user.role
                refresh['ward_id'] = user.ward_id
                
                return response.Response({
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                    "user": {
                        "id": str(user.id),
                        "email": user.email,
                        "name": user.name,
                        "role": user.role,
                        "ward_id": user.ward_id
                    }
                }, status=status.HTTP_200_OK)
            else:
                otp.failed_attempts += 1
                otp.save()
                if otp.failed_attempts >= 5:
                    return response.Response({"error": "Maximum attempts reached. OTP invalidated."}, status=status.HTTP_429_TOO_MANY_REQUESTS)
                return response.Response({"error": "Invalid OTP code"}, status=status.HTTP_400_BAD_REQUEST)
                
        except User.DoesNotExist:
            return response.Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
