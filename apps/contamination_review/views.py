from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiResponse
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.http import Http404

from .models import Pickup
from .serializers import ContaminationPickupSerializer

class ReviewQueueListView(APIView):
    serializer_class = ContaminationPickupSerializer
    """
    GET /api/review-queue/
    Returns all pickups where needs_review = True, ordered by created_at DESC.
    """
    @extend_schema(tags=['Contamination Review'])
    def get(self, request, *args, **kwargs):
        pickups = Pickup.objects.filter(needs_review=True).order_by('-created_at')
        serializer = ContaminationPickupSerializer(pickups, many=True, context={'request': request})
        # Empty list is handled natively by passing empty queryset
        return Response(serializer.data, status=status.HTTP_200_OK)

class PickupCreateView(APIView):
    serializer_class = ContaminationPickupSerializer
    """
    POST /api/pickups/
    Creates a new pickup processing AI predictions automatically.
    """
    @extend_schema(tags=['Contamination Review'])
    def post(self, request, *args, **kwargs):
        serializer = ContaminationPickupSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PickupConfirmAPIView(APIView):
    """
    POST /api/pickups/{id}/confirm/
    Accepts the AI result without modifying points.
    Sets needs_review = False.
    """
    def get_object(self, pk):
        try:
            return Pickup.objects.get(pk=pk)
        except Pickup.DoesNotExist:
            raise Http404

    @extend_schema(
        responses={
            200: ContaminationPickupSerializer,
            404: OpenApiResponse(description="Pickup not found.")
        },
        tags=['Contamination Review']
    )
    @transaction.atomic
    def post(self, request, pk, *args, **kwargs):
        try:
            pickup = self.get_object(pk)
        except Http404:
            return Response({"error": "Pickup not found."}, status=status.HTTP_404_NOT_FOUND)

        pickup.needs_review = False
        pickup.save()
        
        serializer = ContaminationPickupSerializer(pickup, context={'request': request})
        return Response(
            {"message": "Pickup confirmed successfully.", "data": serializer.data}, 
            status=status.HTTP_200_OK
        )

class PickupOverrideCleanAPIView(APIView):
    """
    POST /api/pickups/{id}/override-clean/
    Overrides AI prediction marking it 'clean'.
    Removes contamination flag, sets needs_review to False, adds 5 points.
    """
    def get_object(self, pk):
        try:
            return Pickup.objects.get(pk=pk)
        except Pickup.DoesNotExist:
            raise Http404

    @extend_schema(
        responses={
            200: ContaminationPickupSerializer,
            404: OpenApiResponse(description="Pickup not found.")
        },
        tags=['Contamination Review']
    )
    @transaction.atomic
    def post(self, request, pk, *args, **kwargs):
        try:
            pickup = self.get_object(pk)
        except Http404:
            return Response({"error": "Pickup not found."}, status=status.HTTP_404_NOT_FOUND)

        pickup.contamination_flag = False
        pickup.needs_review = False
        pickup.points_awarded += 5
        pickup.save()
        
        serializer = ContaminationPickupSerializer(pickup, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
