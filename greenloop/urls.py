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
from apps.pickups.views import PickupViewSet
from apps.routes.views import RouteViewSet

router = routers.DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'wards', WardViewSet)
router.register(r'pickups', PickupViewSet)
router.register(r'routes', RouteViewSet)

urlpatterns = [
    path('', RedirectView.as_view(url='/api/docs/', permanent=False)),
    path('admin/', admin.site.urls),

    # API v1
    path('api/v1/', include(router.urls)),

    # OpenAPI Schema & Docs
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # Auth
    path('api/v1/auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/v1/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
