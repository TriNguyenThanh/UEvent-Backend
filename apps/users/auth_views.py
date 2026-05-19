from rest_framework import serializers as drf_serializers
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from common.keycloak_admin import KeycloakAdminError, logout_keycloak_refresh_token
from common.response_codes import ResponseCode
from common.responses import error_response, success_response


class MobileLogoutInputSerializer(drf_serializers.Serializer):
    refresh_token = drf_serializers.CharField(allow_blank=False)


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
