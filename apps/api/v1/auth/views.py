import logging

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema

from apps.users.models import User
from apps.api.throttles import LoginRateThrottle
from .serializers import (
    AuthResponseSerializer,
    LoginSerializer,
    LogoutSerializer,
    RegisterSerializer,
    UserSerializer,
)

logger = logging.getLogger(__name__)


def _build_token_response(user: User) -> dict:
    refresh = RefreshToken.for_user(user)
    return {
        "user": UserSerializer(user).data,
        "tokens": {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        },
    }


class RegisterView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=RegisterSerializer, responses={201: AuthResponseSerializer})
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        payload = _build_token_response(user)
        logger.info("user_registered", extra={"user_id": user.pk, "email": user.email})
        return Response(payload, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]

    @extend_schema(request=LoginSerializer, responses={200: AuthResponseSerializer})
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        payload = _build_token_response(user)
        logger.info("user_logged_in", extra={"user_id": user.pk, "email": user.email})
        return Response(payload, status=status.HTTP_200_OK)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=LogoutSerializer, responses={204: None})
    def post(self, request):
        refresh_token = request.data.get("refresh")
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except TokenError:
                pass
        logger.info("user_logged_out", extra={"user_id": request.user.pk})
        return Response(status=status.HTTP_204_NO_CONTENT)
