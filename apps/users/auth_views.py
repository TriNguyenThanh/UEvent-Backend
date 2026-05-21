from rest_framework import serializers as drf_serializers
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from common.keycloak_admin import (
    KeycloakAdminError,
    logout_keycloak_refresh_token,
    refresh_keycloak_token,
)
from common.response_codes import ResponseCode
from common.responses import error_response, success_response


class MobileLogoutInputSerializer(drf_serializers.Serializer):
    refresh_token = drf_serializers.CharField(allow_blank=False)


class MobileRefreshInputSerializer(drf_serializers.Serializer):
    refresh_token = drf_serializers.CharField(allow_blank=False)


class MobileTokenRefreshView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = MobileRefreshInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            token_data = refresh_keycloak_token(
                serializer.validated_data["refresh_token"]
            )
        except KeycloakAdminError as exc:
            if exc.status_code in (400, 401):
                return error_response(
                    code=ResponseCode.INVALID_CREDENTIALS,
                    message="Refresh token is invalid or expired.",
                    errors={"detail": str(exc)},
                    status_code=status.HTTP_401_UNAUTHORIZED,
                )
            return error_response(
                code=ResponseCode.SERVICE_UNAVAILABLE,
                message="Cannot refresh token with Keycloak.",
                errors={"detail": str(exc)},
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return success_response(
            data={
                "access_token": token_data.get("access_token", ""),
                "refresh_token": token_data.get(
                    "refresh_token",
                    serializer.validated_data["refresh_token"],
                ),
                "token_type": token_data.get("token_type", "Bearer"),
                "expires_in": token_data.get("expires_in", 300),
                "refresh_expires_in": token_data.get("refresh_expires_in", 1800),
                "id_token": token_data.get("id_token"),
            },
            message="Token refreshed successfully.",
        )


class MobileLogoutView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = MobileLogoutInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            logout_keycloak_refresh_token(serializer.validated_data["refresh_token"])
        except KeycloakAdminError as exc:
            return error_response(
                code=ResponseCode.SERVICE_UNAVAILABLE,
                message="Cannot complete logout with Keycloak.",
                errors={"detail": str(exc)},
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return success_response(data=None, message="Logout successful.")
