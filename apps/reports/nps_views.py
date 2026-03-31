from rest_framework import permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Avg

from drf_spectacular.utils import extend_schema
from .models import NPSSurvey
from .nps_serializers import (
    NPSSurveySubmitSerializer,
    NPSSurveyResponseSerializer,
    NPSSummarySerializer,
)

NPS_TRIGGER_DAYS = 30   # Show survey after 30 days of registration
NPS_COOLDOWN_DAYS = 60  # Don't show again for 60 days after submission


class NPSSurveyStatusView(APIView):
    """
    GET /api/v1/nps/status/
    Returns whether the NPS survey should be shown to the resident.
    Conditions:
      1. User is a RESIDENT.
      2. 30 days have passed since registration.
      3. Either never submitted, or next_prompt_at has passed.
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["NPS Survey"],
        responses={200: OpenApiResponse(description="Returns survey status (show/don't show)")}
    )
    def get(self, request):
        user = request.user
        if user.role != "RESIDENT":
            return Response({"show_survey": False})

        days_since_register = (timezone.now() - user.created_at).days
        if days_since_register < NPS_TRIGGER_DAYS:
            return Response({
                "show_survey": False,
                "reason": f"Only {days_since_register} days since registration (need {NPS_TRIGGER_DAYS})"
            })

        try:
            survey = user.nps_survey
            if survey.next_prompt_at > timezone.now():
                return Response({
                    "show_survey": False,
                    "reason": "Survey cooldown active",
                    "next_prompt_at": survey.next_prompt_at
                })
            # Cooldown expired — allow re-prompt
            return Response({"show_survey": True})
        except NPSSurvey.DoesNotExist:
            return Response({"show_survey": True})


class NPSSurveySubmitView(APIView):
    serializer_class = NPSSurveySubmitSerializer
    """
    POST /api/v1/nps/submit/
    Accepts { score: 0-10, comment: "" }
    Creates or updates the NPSSurvey for the resident.
    Resets the 60-day cooldown on each submission.
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(tags=["NPS Survey"], request=NPSSurveySubmitSerializer)
    def post(self, request):
        user = request.user
        if user.role != "RESIDENT":
            return Response(
                {"error": "Only residents can submit NPS surveys."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = NPSSurveySubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        next_prompt = timezone.now() + timezone.timedelta(days=NPS_COOLDOWN_DAYS)

        survey, created = NPSSurvey.objects.update_or_create(
            resident=user,
            defaults={
                "score": serializer.validated_data["score"],
                "comment": serializer.validated_data.get("comment", ""),
                "next_prompt_at": next_prompt,
            },
        )

        out = NPSSurveyResponseSerializer(survey)
        return Response(
            out.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class NPSSummaryView(APIView):
    """
    GET /api/v1/nps/summary/
    Admin-only. Returns calculated NPS score and feedback summary.
    NPS = (% Promoters - % Detractors) × 100
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(tags=["NPS Survey"], responses=NPSSummarySerializer)
    def get(self, request):
        if request.user.role != "ADMIN":
            return Response(
                {"error": "Admin access required."},
                status=status.HTTP_403_FORBIDDEN,
            )

        surveys = NPSSurvey.objects.select_related("resident").all()
        total = surveys.count()

        if total == 0:
            return Response({
                "total_responses": 0,
                "nps_score": 0.0,
                "promoters": 0,
                "passives": 0,
                "detractors": 0,
                "average_score": 0.0,
                "recent_comments": [],
            })

        promoters  = surveys.filter(score__gte=9).count()
        passives   = surveys.filter(score__gte=7, score__lte=8).count()
        detractors = surveys.filter(score__lte=6).count()

        nps_score = ((promoters - detractors) / total) * 100
        avg_score = surveys.aggregate(avg=Avg("score"))["avg"] or 0.0

        recent_comments = list(
            surveys.exclude(comment="")
            .order_by("-submitted_at")[:10]
            .values("resident__name", "score", "comment", "submitted_at")
        )

        return Response({
            "total_responses": total,
            "nps_score": round(nps_score, 1),
            "promoters": promoters,
            "passives": passives,
            "detractors": detractors,
            "average_score": round(avg_score, 2),
            "recent_comments": recent_comments,
        })
