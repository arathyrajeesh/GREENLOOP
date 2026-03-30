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
from apps.users.views import UserViewSet, WorkerRecyclerCreateAPIView
from apps.wards.views import WardViewSet
from apps.pickups.views import PickupViewSet, PickupVerificationViewSet
from apps.routes.views import RouteViewSet, TodayRouteView
from apps.attendance.views import AttendanceLogViewSet, WorkerAttendanceView
from apps.complaints.views import ComplaintViewSet
from apps.rewards.views import (
    RewardViewSet, RewardRedemptionViewSet, 
    RewardSettingsViewSet, RewardItemManagementViewSet
)
from apps.payments.views import FeeCollectionViewSet
from apps.recyclers.views import MaterialTypeViewSet, RecyclerPurchaseViewSet, RecyclingCertificateViewSet
from apps.notifications.views import NotificationViewSet
from apps.accounts.views import (
    OTPCodeViewSet, OTPRequestView, OTPVerifyView, 
    PingView, MigrateView, LogoutView, WorkerLoginView, AdminLoginView
)
from apps.dashboard.views import SyncQueueViewSet
from apps.reports.views import ReportCategoryViewSet, ReportViewSet, WardCollectionReportViewSet
from apps.reports.nps_views import NPSSurveyStatusView, NPSSurveySubmitView, NPSSummaryView

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
router.register(r'reward-settings', RewardSettingsViewSet, basename='reward-settings')
router.register(r'reward-items', RewardItemManagementViewSet, basename='reward-item')
router.register(r'payments', FeeCollectionViewSet, basename='payment')
# Recycler Router for /api/v1/recycler/ prefix
recycler_router = routers.DefaultRouter()
recycler_router.register(r'materials', MaterialTypeViewSet, basename='materialtype')
recycler_router.register(r'purchases', RecyclerPurchaseViewSet, basename='recyclerpurchase')
recycler_router.register(r'certificates', RecyclingCertificateViewSet, basename='recycling-certificate')

router.register(r'notifications', NotificationViewSet, basename='notification')
router.register(r'otp-codes', OTPCodeViewSet, basename='otpcode')
router.register(r'sync', SyncQueueViewSet, basename='sync')
router.register(r'report-categories', ReportCategoryViewSet, basename='reportcategory')
router.register(r'reports', ReportViewSet, basename='report')
router.register(r'ward-reports', WardCollectionReportViewSet, basename='wardcollectionreport')

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
    path('api/v1/users/create-worker/', WorkerRecyclerCreateAPIView.as_view(), name='create-worker'),
    path('api/v1/recycler/', include(recycler_router.urls)),
    path('api/v1/', include(router.urls)),
    path('', include('apps.contamination_review.urls')),

    # NPS Survey
    path('api/v1/nps/status/', NPSSurveyStatusView.as_view(), name='nps-status'),
    path('api/v1/nps/submit/', NPSSurveySubmitView.as_view(), name='nps-submit'),
    path('api/v1/nps/summary/', NPSSummaryView.as_view(), name='nps-summary'),

    # OpenAPI Schema & Docs
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # Auth
    path('api/v1/auth/ping/', PingView.as_view(), name='ping'),
    path('api/v1/auth/migrate/', MigrateView.as_view(), name='migrate'),
    path('api/v1/auth/otp/request/', OTPRequestView.as_view(), name='otp_request'),
    path('api/v1/auth/otp/verify/', OTPVerifyView.as_view(), name='otp_verify'),
    path('api/v1/auth/worker-login/', WorkerLoginView.as_view(), name='worker_login'),
    path('api/v1/auth/admin-login/', AdminLoginView.as_view(), name='admin_login'),
    path('api/v1/auth/logout/', LogoutView.as_view(), name='logout'),
    path('api/v1/auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/v1/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

]
from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
