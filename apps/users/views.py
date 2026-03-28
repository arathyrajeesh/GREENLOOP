from rest_framework import viewsets, permissions, views, status, response
from apps.users.models import User
from apps.users.serializers import UserSerializer, WorkerRecyclerCreateSerializer
from drf_spectacular.utils import extend_schema

@extend_schema(tags=['Admin'])
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

@extend_schema(tags=['Admin'])
class WorkerRecyclerCreateAPIView(views.APIView):
    permission_classes = [permissions.IsAdminUser]

    @extend_schema(request=WorkerRecyclerCreateSerializer, responses={201: UserSerializer})
    def post(self, request):
        serializer = WorkerRecyclerCreateSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return response.Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)
        return response.Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
