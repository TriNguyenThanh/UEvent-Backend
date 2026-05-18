from typing import Any

from django.conf import settings
from django.db import IntegrityError
from django.utils import timezone
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from rest_framework import serializers as drf_serializers
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from apps.users.models import UserAuthIdentity
from common.authentication import KeycloakJWTAuthentication
from common.keycloak_admin import (
    KeycloakAdminError,
    exchange_token_for_user,
    get_or_create_keycloak_user,
)
from common.response_codes import ResponseCode
from common.responses import error_response, success_response


class GoogleVerifyInputSerializer(drf_serializers.Serializer):
    id_token = drf_serializers.CharField()


class GoogleTokenOutputSerializer(drf_serializers.Serializer):
    access_token = drf_serializers.CharField()
    refresh_token = drf_serializers.CharField()
    token_type = drf_serializers.CharField()
    expires_in = drf_serializers.IntegerField()
    refresh_expires_in = drf_serializers.IntegerField()


class GoogleVerifyView(APIView):
    """
    POST /api/v1/auth/google/verify/

    Xác minh Google ID token từ native Google Sign-In, đồng bộ user qua
    Keycloak, rồi trả Keycloak tokens cho app.
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="Verify native Google Sign-In",
        operation_description=(
            "App gửi Google ID token lấy từ native Google Sign-In. Backend xác minh "
            "token với Google, tạo/cập nhật user trong Keycloak, thực hiện Token "
            "Exchange và trả access_token/refresh_token cho app."
        ),
        request_body=GoogleVerifyInputSerializer,
        responses={
            200: GoogleTokenOutputSerializer(),
            400: openapi.Response("Google token không hợp lệ hoặc email chưa xác minh."),
            503: openapi.Response("Không thể kết nối Google hoặc Keycloak."),
        },
        tags=["Mobile Auth"],
    )
    def post(self, request):
        serializer = GoogleVerifyInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            google_payload = _verify_google_id_token(serializer.validated_data["id_token"])
        except ValueError as exc:
            return error_response(
                code=ResponseCode.INVALID_CREDENTIALS,
                message="Token Google không hợp lệ. Vui lòng đăng nhập lại.",
                errors={"detail": str(exc)},
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        except RuntimeError as exc:
            return error_response(
                code=ResponseCode.SERVICE_UNAVAILABLE,
                message="Chưa cấu hình Google OAuth client cho backend.",
                errors={"detail": str(exc)},
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        email = _claim_text(google_payload, "email").lower()
        if not email or google_payload.get("email_verified") is not True:
            return error_response(
                code=ResponseCode.INVALID_CREDENTIALS,
                message="Email Google chưa được xác minh. Vui lòng dùng tài khoản đã xác minh email.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            keycloak_user_id = get_or_create_keycloak_user(
                email,
                full_name=_claim_text(google_payload, "name"),
                first_name=_claim_text(google_payload, "given_name"),
                last_name=_claim_text(google_payload, "family_name"),
                avatar_url=_claim_text(google_payload, "picture"),
            )
            token_data = exchange_token_for_user(keycloak_user_id)
            user, _ = KeycloakJWTAuthentication().authenticate_token(token_data["access_token"])
            _link_google_identity(user, google_payload)
        except KeycloakAdminError as exc:
            return error_response(
                code=ResponseCode.SERVICE_UNAVAILABLE,
                message="Không thể hoàn tất đăng nhập Google. Vui lòng thử lại sau.",
                errors={"detail": str(exc)},
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except (AuthenticationFailed, KeyError, IntegrityError) as exc:
            return error_response(
                code=ResponseCode.INVALID_CREDENTIALS,
                message="Không thể xác thực tài khoản Google với hệ thống. Vui lòng thử lại.",
                errors={"detail": str(exc)},
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        output = GoogleTokenOutputSerializer(
            {
                "access_token": token_data["access_token"],
                "refresh_token": token_data.get("refresh_token", ""),
                "token_type": token_data.get("token_type", "Bearer"),
                "expires_in": token_data.get("expires_in", 300),
                "refresh_expires_in": token_data.get("refresh_expires_in", 1800),
            }
        )
        return success_response(
            data=output.data,
            message="Đăng nhập Google thành công.",
        )


def _verify_google_id_token(raw_id_token: str) -> dict[str, Any]:
    client_ids = [client_id.strip() for client_id in settings.GOOGLE_OAUTH_CLIENT_IDS if client_id.strip()]
    if not client_ids:
        raise RuntimeError("GOOGLE_OAUTH_CLIENT_IDS is empty.")

    verifier_request = google_requests.Request()
    last_error: ValueError | None = None
    for client_id in client_ids:
        try:
            return google_id_token.verify_oauth2_token(
                raw_id_token,
                verifier_request,
                client_id,
            )
        except ValueError as exc:
            last_error = exc

    raise ValueError(str(last_error) if last_error else "Google token audience is not allowed.")


def _link_google_identity(user, google_payload: dict[str, Any]) -> None:
    google_subject = _claim_text(google_payload, "sub")
    if not google_subject:
        raise AuthenticationFailed("Google token missing subject.")

    now = timezone.now()
    existing = UserAuthIdentity.objects.filter(
        provider=UserAuthIdentity.Provider.GOOGLE,
        provider_subject=google_subject,
    ).first()
    if existing and existing.user_id != user.id:
        raise AuthenticationFailed("Google identity is already linked to another user.")

    UserAuthIdentity.objects.update_or_create(
        provider=UserAuthIdentity.Provider.GOOGLE,
        provider_subject=google_subject,
        defaults={
            "user": user,
            "email_verified": True,
            "last_login_at": now,
        },
    )


def _claim_text(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    return value.strip() if isinstance(value, str) else ""
