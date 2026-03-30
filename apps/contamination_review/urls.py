from django.urls import path
from .views import (
    ReviewQueueListView,
    PickupCreateView, 
    PickupConfirmAPIView,
    PickupOverrideCleanAPIView
)

urlpatterns = [
    path('api/review-queue/', ReviewQueueListView.as_view(), name='review-queue'),
    path('api/pickups/', PickupCreateView.as_view(), name='create-pickup'),
    path('api/pickups/<int:pk>/confirm/', PickupConfirmAPIView.as_view(), name='confirm-pickup'),
    path('api/pickups/<int:pk>/override-clean/', PickupOverrideCleanAPIView.as_view(), name='override-clean'),
]
