import random
import string
from rest_framework import viewsets, permissions, views, status, response
from rest_framework_simplejwt.tokens import RefreshToken
from django.conf import settings
from apps.users.models import User
from .models import OTPCode
from .serializers import OTPCodeSerializer

class OTPCodeViewSet(viewsets.ModelViewSet):
    queryset = OTPCode.objects.all()
    serializer_class = OTPCodeSerializer
    permission_classes = [permissions.IsAuthenticated]

class OTPRequestView(views.APIView):
    permission_classes = [permissions.AllowAny]
    throttle_scope = 'otp_request'

    def post(self, request):
        email = request.data.get('email')
        if not email:
            return response.Response({"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get or create resident user
        user, created = User.objects.get_or_create(
            email=email, 
            defaults={'name': email.split('@')[0], 'role': 'RESIDENT'}
        )
        
        # Generate 6-digit OTP
        otp_code = ''.join(random.choices(string.digits, k=6))
        OTPCode.objects.create(user=user, code=otp_code)
        
        # Placeholder for sending email
        # print(f"DEBUG: Sending OTP {otp_code} to {email}")
        
        return response.Response({
            "message": "OTP sent successfully",
            "is_new_user": created
        }, status=status.HTTP_200_OK)

class OTPVerifyView(views.APIView):
    permission_classes = [permissions.AllowAny]

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
