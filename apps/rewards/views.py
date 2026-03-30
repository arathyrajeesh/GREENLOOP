from django.db import models
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Reward, RewardRedemption, RewardItem, RewardSettings
from .serializers import (
    RewardSerializer, RewardRedemptionSerializer, 
    RewardItemSerializer, RewardSettingsSerializer
)
from .utils import calculate_streak
from .permissions import IsAdminUser

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

    @action(detail=False, methods=['get'])
    def balance(self, request):
        user = request.user
        balance = Reward.objects.filter(resident=user).aggregate(models.Sum('points'))['points__sum'] or 0
        return Response({"balance": balance})

    @action(detail=False, methods=['get'])
    def history(self, request):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
             serializer = self.get_serializer(page, many=True)
             return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def summary(self, request):
        user = request.user
        balance = Reward.objects.filter(resident=user).aggregate(models.Sum('points'))['points__sum'] or 0
        streak = calculate_streak(user)
        recent_history = Reward.objects.filter(resident=user).order_by('-created_at')[:5]
        history_serializer = RewardSerializer(recent_history, many=True)
        
        return Response({
            "balance": balance,
            "streak": streak,
            "streak_message": f"{streak} weeks of perfect segregation!" if streak > 0 else "Start your segregation streak today!",
            "recent_history": history_serializer.data
        })

    @action(detail=False, methods=['get'])
    def items(self, request):
        items = RewardItem.objects.filter(is_active=True)
        serializer = RewardItemSerializer(items, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def streak(self, request):
        streak = calculate_streak(request.user)
        return Response({
            "streak": streak,
            "message": f"{streak} weeks of perfect segregation!" if streak >= 1 else "Keep going to build your streak!"
        })

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

class RewardSettingsViewSet(viewsets.ModelViewSet):
    queryset = RewardSettings.objects.all()
    serializer_class = RewardSettingsSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]

    def list(self, request, *args, **kwargs):
        settings = RewardSettings.get_settings()
        serializer = self.get_serializer(settings)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        # We only want one settings object
        settings = RewardSettings.get_settings()
        serializer = self.get_serializer(settings, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

class RewardItemManagementViewSet(viewsets.ModelViewSet):
    queryset = RewardItem.objects.all()
    serializer_class = RewardItemSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
