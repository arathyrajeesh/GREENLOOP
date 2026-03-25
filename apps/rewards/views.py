from rest_framework import viewsets, permissions
from .models import Reward, RewardRedemption
from .serializers import RewardSerializer, RewardRedemptionSerializer

class RewardViewSet(viewsets.ModelViewSet):
    serializer_class = RewardSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Reward.objects.none()
            
        user = self.request.user
        if not user or user.is_anonymous:
            return Reward.objects.none()
            
        if user.role == 'RESIDENT':
            return Reward.objects.filter(resident=user)
        return Reward.objects.all()

class RewardRedemptionViewSet(viewsets.ModelViewSet):
    serializer_class = RewardRedemptionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return RewardRedemption.objects.none()
            
        user = self.request.user
        if not user or user.is_anonymous:
            return RewardRedemption.objects.none()
            
        if user.role == 'RESIDENT':
            return RewardRedemption.objects.filter(resident=user)
        return RewardRedemption.objects.all()
