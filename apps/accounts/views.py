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
from django.db import connection
from rest_framework_simplejwt.tokens import RefreshToken
from .utils import send_resend_email
from .serializers import (
    OTPCodeSerializer, 
    OTPRequestSerializer, 
    OTPVerifySerializer,
    BaseResponseSerializer,
    LogoutSerializer,
    LogoutSerializer,
    WorkerLoginSerializer,
    AdminLoginSerializer
)
from django.contrib.auth import authenticate

class OTPCodeViewSet(viewsets.ModelViewSet):
    queryset = OTPCode.objects.all()
    serializer_class = OTPCodeSerializer
    permission_classes = [permissions.IsAuthenticated]

class PingView(views.APIView):
    """
    Diagnostic view to check database and model health in production.
    """
    permission_classes = [permissions.AllowAny]
    @extend_schema(responses={200: BaseResponseSerializer})

    def get(self, request):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
                tables = [row[0] for row in cursor.fetchall()]

            user_count = User.objects.count() if 'users_user' in tables else "Table Missing"
            otp_count = OTPCode.objects.count() if 'accounts_otpcode' in tables else "Table Missing"
            
            return response.Response({
                "status": "ok",
                "database": "connected",
                "tables": tables,
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

    @extend_schema(responses={200: BaseResponseSerializer})
    def get(self, request):
        mode = request.query_params.get('type', 'standard')
        try:
            if mode == 'showmigrations':
                import io
                out = io.StringIO()
                call_command('showmigrations', stdout=out)
                return response.Response({
                    "status": "success",
                    "migrations": out.getvalue()
                })

            if mode == 'reset_nuclear':
                # Last resort: drop everything and start over, but skip views to avoid PostGIS/system issues
                print("NUCLEAR RESET: Dropping all tables in public schema (skipping views/PostGIS internals)...")
                with connection.cursor() as cursor:
                    cursor.execute("""
                        DO $$ DECLARE
                            r RECORD;
                        BEGIN
                            -- Drop tables, skipping spatial_ref_sys
                            FOR r IN (
                                SELECT tablename FROM pg_tables 
                                WHERE schemaname = 'public' 
                                AND tablename NOT IN ('spatial_ref_sys')
                            ) LOOP
                                EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
                            END LOOP;
                        END $$;
                    """)
                if not connection.get_autocommit():
                    connection.commit()
                
                print("All dropped. Running migrate...")
                call_command('migrate', interactive=False)
                return response.Response({
                    "status": "success", 
                    "message": "Nuclear reset successful. Database schema recreated from scratch."
                })

            if mode == 'fix_hard':
                # Aggressive fix: manually clear migration history for problematic apps
                print("Running aggressive migration fix (raw SQL) with explicit commit...")
                with connection.cursor() as cursor:
                    # We must clear all apps that depend on User OR were applied before User was custom
                    apps_to_clear = ['admin', 'auth', 'sessions', 'contenttypes', 'users']
                    for app in apps_to_clear:
                        print(f"Clearing migrations for: {app}")
                        cursor.execute(f"DELETE FROM django_migrations WHERE app = '{app}';")
                
                # Manual commit to ensure SQL is applied BEFORE call_command
                if not connection.get_autocommit():
                    connection.commit()
                
                print("History cleared. Now running migrate --fake-initial...")
                # Now try to migrate again with fake-initial to handle existing tables
                call_command('migrate', fake_initial=True, interactive=False)
                return response.Response({
                    "status": "success",
                    "message": "Aggressive migration fix successful. History cleared and migrations applied."
                })

            if mode == 'fix':
                # Emergency fix for "InconsistentMigrationHistory"
                # This happens when switching to custom AUTH_USER_MODEL on existing DB
                print("Running emergency migration fix...")
                call_command('migrate', 'contenttypes', fake=True, interactive=False)
                call_command('migrate', 'auth', fake=True, interactive=False)
                call_command('migrate', 'users', fake=True, interactive=False)
                call_command('migrate', fake_initial=True, interactive=False)
                return response.Response({
                    "status": "success",
                    "message": "Emergency migration fix (faking) applied."
                })

            if mode == 'promote_admin':
                # Promote any existing user to superuser via raw SQL
                # Usage: GET /api/v1/auth/migrate/?type=promote_admin&email=admin@gmail.com&password=admin135
                email = request.query_params.get('email')
                passwd = request.query_params.get('password')
                if not email:
                    return response.Response({"status": "error", "message": "Provide ?email=..."}, status=status.HTTP_400_BAD_REQUEST)
                
                from apps.users.models import User
                from django.contrib.auth.hashers import make_password
                
                # Check if user exists; create if not
                user, created = User.objects.get_or_create(
                    email=email,
                    defaults={'name': 'Admin', 'role': 'ADMIN'}
                )
                
                # Set superuser flags and password
                user.is_staff = True
                user.is_superuser = True
                user.is_active = True
                if passwd:
                    user.set_password(passwd)
                user.save()
                
                action = "created and promoted" if created else "promoted"
                return response.Response({
                    "status": "success",
                    "message": f"User {email} {action} to superuser. Login at /admin with this email and password."
                })

            if mode == 'create_superuser':
                # Bootstrap an admin superuser on Render where no shell access is available
                # Usage: GET /api/v1/auth/migrate/?type=create_superuser&email=you@example.com&password=yourpassword
                from apps.users.models import User
                email = request.query_params.get('email')
                passwd = request.query_params.get('password')
                if not email or not passwd:
                    return response.Response({
                        "status": "error",
                        "message": "Provide ?email=...&password=... query params"
                    }, status=status.HTTP_400_BAD_REQUEST)
                if User.objects.filter(email=email).exists():
                    return response.Response({
                        "status": "info",
                        "message": f"User with email {email} already exists."
                    })
                User.objects.create_superuser(email=email, password=passwd)
                return response.Response({
                    "status": "success",
                    "message": f"Superuser {email} created. Visit /admin to login."
                })
            
            # Trigger standard migrate command
            print("Running standard migrations...")
            call_command('migrate', interactive=False)
            return response.Response({
                "status": "success",
                "message": "Migrations applied successfully."
            })
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"MIGRATION ERROR:\n{error_details}")
            return response.Response({
                "status": "error",
                "message": str(e),
                "traceback": error_details if settings.DEBUG else "Traceback hidden"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class OTPRequestView(views.APIView):
    permission_classes = [permissions.AllowAny]
    throttle_scope = 'otp_request'

    @extend_schema(
        request=OTPRequestSerializer, 
        responses={200: BaseResponseSerializer},
        tags=['Resident', 'Auth']
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
        
        # Send via custom Resend HTTPS utility (bypasses Django SMTP and Render blocks)
        subject = "GreenLoop Login OTP"
        html_content = f"<p>Your GreenLoop login OTP is <strong>{otp_code}</strong>. It is valid for 5 minutes.</p>"
        
        email_sent, error_info = send_resend_email(email, subject, html_content)
        
        if email_sent:
            return response.Response({
                "message": "OTP sent to email",
                "email_sent": True
            }, status=status.HTTP_200_OK)
        else:
            return response.Response({
                "message": "Email failed, using fallback OTP",
                "email_sent": False,
                "otp": otp_code,
                "details": error_info # Good for debugging
            }, status=status.HTTP_200_OK) # returning 200 so frontend can handle it easily

class OTPVerifyView(views.APIView):
    serializer_class = OTPVerifySerializer
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        request=OTPVerifySerializer, 
        responses={200: BaseResponseSerializer},
        tags=['Resident', 'Auth']
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

class LogoutView(views.APIView):
    """
    Blacklist the refresh token to logout the user.
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=LogoutSerializer,
        responses={200: BaseResponseSerializer},
        description="Blacklist the refresh token to logout the user.",
        tags=['Auth', 'Shared']
    )
    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if not refresh_token:
                return response.Response({"message": "Refresh token is required"}, status=status.HTTP_400_BAD_REQUEST)
            
            token = RefreshToken(refresh_token)
            token.blacklist()
            return response.Response(
                {"message": "Successfully logged out"},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return response.Response(
                {"message": "Invalid token or already blacklisted"},
                status=status.HTTP_400_BAD_REQUEST
            )

class WorkerLoginView(views.APIView):
    serializer_class = WorkerLoginSerializer
    permission_classes = [permissions.AllowAny]
    
    @extend_schema(
        request=WorkerLoginSerializer,
        responses={200: BaseResponseSerializer},
        tags=['HKS Worker', 'Admin', 'Auth']
    )
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            return response.Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        username = serializer.validated_data.get('username')
        password = serializer.validated_data.get('password')
        
        user = authenticate(request, username=username, password=password)
        if not user:
            return response.Response({"error": "Invalid credentials providing username/password"}, status=status.HTTP_401_UNAUTHORIZED)
            
        if not user.is_active:
            return response.Response({"error": "This account is inactive."}, status=status.HTTP_401_UNAUTHORIZED)
            
        # Constraint: Allow HKS_WORKER only
        if user.role != 'HKS_WORKER':
             return response.Response({"error": "This login point is restricted to HKS workers. Recyclers must use the Recycler Login."}, status=status.HTTP_403_FORBIDDEN)
             
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        refresh['role'] = user.role
        refresh['ward_id'] = str(user.ward_id) if user.ward_id else None
        
        return response.Response({
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": {
                "id": str(user.id),
                "username": user.username,
                "email": user.email,
                "name": user.name,
                "role": user.role,
                "ward_id": user.ward_id
            }
        }, status=status.HTTP_200_OK)



class AdminLoginView(views.APIView):
    """
    Separate login endpoint for system administrators.
    """
    serializer_class = AdminLoginSerializer
    permission_classes = [permissions.AllowAny]
    
    @extend_schema(
        request=AdminLoginSerializer,
        responses={200: BaseResponseSerializer},
        tags=['Admin', 'Auth']
    )
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            return response.Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        email = serializer.validated_data.get('email')
        password = serializer.validated_data.get('password')
        
        user = authenticate(request, username=email, password=password)
        if not user or not user.is_active:
            return response.Response({"error": "Invalid administrative credentials or account inactive."}, status=status.HTTP_401_UNAUTHORIZED)
            
        # Constraint: Allow ADMIN only
        if user.role != 'ADMIN':
             return response.Response({"error": "This login point is restricted to system administrators."}, status=status.HTTP_403_FORBIDDEN)
             
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        refresh['role'] = user.role
        
        return response.Response({
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": {
                "id": str(user.id),
                "username": user.username,
                "email": user.email,
                "name": user.name,
                "role": user.role,
                "token_type": "ADMIN_TOKEN"
            }
        }, status=status.HTTP_200_OK)


class RecyclerLoginView(views.APIView):
    """
    Dedicated login endpoint for recycling facilities.
    """
    serializer_class = WorkerLoginSerializer
    permission_classes = [permissions.AllowAny]
    
    @extend_schema(
        request=WorkerLoginSerializer,
        responses={200: BaseResponseSerializer},
        tags=['Recycler', 'Auth']
    )
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            return response.Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        username = serializer.validated_data.get('username')
        password = serializer.validated_data.get('password')
        
        user = authenticate(request, username=username, password=password)
        if not user or not user.is_active:
            return response.Response({"error": "Invalid recycler credentials or account inactive."}, status=status.HTTP_401_UNAUTHORIZED)
            
        # Constraint: Allow RECYCLER only
        if user.role != 'RECYCLER':
             return response.Response({"error": "This login point is restricted to recycling facilities."}, status=status.HTTP_403_FORBIDDEN)
             
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        refresh['role'] = user.role
        
        return response.Response({
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": {
                "id": str(user.id),
                "username": user.username,
                "email": user.email,
                "name": user.name,
                "role": user.role,
                "token_type": "RECYCLER_TOKEN"
            }
        }, status=status.HTTP_200_OK)
