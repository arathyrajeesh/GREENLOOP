from rest_framework import viewsets, permissions, views, status, response
from rest_framework.decorators import action
from apps.users.models import User
from apps.users.serializers import UserSerializer, WorkerRecyclerCreateSerializer
from drf_spectacular.utils import extend_schema

@extend_schema(tags=['Admin'])
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.select_related('ward').all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(tags=['Profile'])
    @action(detail=False, methods=['get', 'patch', 'put'], url_path='me')
    def me(self, request):
        """
        Retrieves or updates the currently authenticated user's profile.
        """
        user = request.user
        if request.method == 'GET':
            serializer = self.get_serializer(user)
            return response.Response(serializer.data)
        
        # PATCH/PUT
        serializer = self.get_serializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return response.Response(serializer.data)

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
