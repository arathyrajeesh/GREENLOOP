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
from .serializers import (
    OTPCodeSerializer, 
    OTPRequestSerializer, 
    OTPVerifySerializer,
    BaseResponseSerializer,
    LogoutSerializer
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
                from django.core.management import call_command
                out = io.StringIO()
                call_command('showmigrations', stdout=out)
                return response.Response({
                    "status": "success",
                    "migrations": out.getvalue()
                })

            if mode == 'reset_nuclear':
                # Last resort: drop everything and start over, but skip PostGIS internals
                print("NUCLEAR RESET: Dropping all tables in public schema (skipping PostGIS)...")
                with connection.cursor() as cursor:
                    cursor.execute("""
                        DO $$ DECLARE
                            r RECORD;
                        BEGIN
                            -- Drop views first, skipping PostGIS internals
                            FOR r IN (
                                SELECT viewname FROM pg_views 
                                WHERE schemaname = 'public' 
                                AND viewname NOT IN ('geography_columns', 'geometry_columns', 'raster_columns', 'raster_overviews')
                            ) LOOP
                                EXECUTE 'DROP VIEW IF EXISTS ' || quote_ident(r.viewname) || ' CASCADE';
                            END LOOP;

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
            
            if mode == 'reset_nuclear':
                # Last resort: drop everything and start over
                print("NUCLEAR RESET: Dropping all tables in public schema...")
                with connection.cursor() as cursor:
                    cursor.execute("""
                        DO $$ DECLARE
                            r RECORD;
                        BEGIN
                            FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
                                EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
                            END LOOP;
                        END $$;
                    """)
                if not connection.get_autocommit():
                    connection.commit()
                
                print("All tables dropped. Running migrate...")
                call_command('migrate', interactive=False)
                return response.Response({
                    "status": "success", 
                    "message": "Nuclear reset successful. Database schema recreated from scratch."
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
    serializer_class = OTPVerifySerializer
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

class LogoutView(views.APIView):
    """
    Blacklist the refresh token to logout the user.
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=LogoutSerializer,
        responses={200: BaseResponseSerializer},
        description="Blacklist the refresh token to logout the user."
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
