from django.db import models
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

    def perform_create(self, serializer):
        user = self.request.user
        
        # Calculate balance
        total_earned = Reward.objects.filter(resident=user, transaction_type='EARNED').aggregate(models.Sum('points'))['points__sum'] or 0
        total_redeemed = Reward.objects.filter(resident=user, transaction_type='REDEEMED').aggregate(models.Sum('points'))['points__sum'] or 0
        # Wait, Reward.points is negative for redeemed in the model definition? 
        # Let's check the model again.
        # "points = models.IntegerField(help_text='Positive for earned, negative for redeemed')"
        # So sum() of all points is the balance.
        balance = Reward.objects.filter(resident=user).aggregate(models.Sum('points'))['points__sum'] or 0
        
        points_spent = serializer.validated_data.get('points_spent', 0)
        
        from rest_framework.exceptions import ValidationError
        if balance < points_spent:
            raise ValidationError("Insufficient points balance for this redemption.")
            
        # Create the redemption and the corresponding Reward record (negative points)
        redemption = serializer.save(resident=user, status='PENDING')
        
        Reward.objects.create(
            resident=user,
            points=-points_spent,
            transaction_type='REDEEMED',
            description=f"Redemption for {redemption.reward_item}"
        )
