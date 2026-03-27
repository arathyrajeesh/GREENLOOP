from django.contrib import admin
from django.urls import path, re_path, include
from django.views.generic import RedirectView
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from rest_framework import routers

# ViewSets
from apps.users.views import UserViewSet
from apps.wards.views import WardViewSet
from apps.pickups.views import PickupViewSet, PickupVerificationViewSet
from apps.routes.views import RouteViewSet, TodayRouteView
from apps.attendance.views import AttendanceLogViewSet, WorkerAttendanceView
from apps.complaints.views import ComplaintViewSet
from apps.rewards.views import RewardViewSet, RewardRedemptionViewSet
from apps.payments.views import FeeCollectionViewSet
from apps.recyclers.views import MaterialTypeViewSet, RecyclerPurchaseViewSet, RecyclingCertificateViewSet
from apps.notifications.views import NotificationViewSet
from apps.accounts.views import OTPCodeViewSet, OTPRequestView, OTPVerifyView, PingView, MigrateView, LogoutView
from apps.dashboard.views import SyncQueueViewSet, LiveMapView
from apps.reports.views import ReportCategoryViewSet, ReportViewSet

router = routers.DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'wards', WardViewSet)
router.register(r'pickups', PickupViewSet, basename='pickup')
router.register(r'pickup-verifications', PickupVerificationViewSet, basename='pickupverification')
router.register(r'routes', RouteViewSet, basename='route')
router.register(r'attendance', AttendanceLogViewSet, basename='attendance')
router.register(r'complaints', ComplaintViewSet, basename='complaint')
router.register(r'rewards', RewardViewSet, basename='reward')
router.register(r'reward-redemptions', RewardRedemptionViewSet, basename='reward-redemption')
router.register(r'payments', FeeCollectionViewSet, basename='payment')
router.register(r'material-types', MaterialTypeViewSet, basename='materialtype')
router.register(r'recycler-purchases', RecyclerPurchaseViewSet, basename='recyclerpurchase')
router.register(r'recycling-certificates', RecyclingCertificateViewSet, basename='recycling-certificate')
router.register(r'notifications', NotificationViewSet, basename='notification')
router.register(r'otp-codes', OTPCodeViewSet, basename='otpcode')
router.register(r'sync-queue', SyncQueueViewSet, basename='syncqueue')
router.register(r'report-categories', ReportCategoryViewSet, basename='reportcategory')
router.register(r'reports', ReportViewSet, basename='report')

from django.http import JsonResponse

def health_check(request):
    return JsonResponse({"status": "healthy", "service": "greenloop-backend"})

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='swagger-ui', permanent=False)),
    path('health/', health_check, name='health-check'),
    path('admin/', admin.site.urls),
    
    # Custom HKS API Endpoints
    path('api/v1/hks/routes/today/', TodayRouteView.as_view(), name='hks-route-today'),
    path('api/v1/hks/attendance/', WorkerAttendanceView.as_view(), name='hks-attendance'),
    path('api/v1/', include(router.urls)),

    # OpenAPI Schema & Docs
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # Auth
    path('api/v1/auth/ping/', PingView.as_view(), name='ping'),
    path('api/v1/auth/migrate/', MigrateView.as_view(), name='migrate'),
    path('api/v1/auth/otp/request/', OTPRequestView.as_view(), name='otp_request'),
    path('api/v1/auth/otp/verify/', OTPVerifyView.as_view(), name='otp_verify'),
    path('api/v1/auth/logout/', LogoutView.as_view(), name='logout'),
    path('api/v1/auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/v1/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
