from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.accounts import selectors, services
from apps.accounts.serializers import (
    CustomTokenObtainPairSerializer,
    MeSerializer,
    StudentRegisterSerializer,
    UserSerializer,
)
from apps.core.permissions import IsAdminStaff


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"


class CustomTokenRefreshView(TokenRefreshView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        user, profile = selectors.get_current_user_profile(user=request.user)
        data = MeSerializer({"user": user, "profile": profile}).data
        return Response(data)


class RegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "register"

    def post(self, request: Request) -> Response:
        serializer = StudentRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = services.register_student(**serializer.validated_data)

        token = CustomTokenObtainPairSerializer.get_token(user)
        data = {
            "user": UserSerializer(user).data,
            "access": str(token.access_token),
            "refresh": str(token),
        }
        return Response(data, status=status.HTTP_201_CREATED)


class AdminUserListView(generics.ListAPIView):
    permission_classes = [IsAdminStaff]
    serializer_class = UserSerializer
    queryset = selectors.list_users()
