"""
OTP Auth Views.

POST /api/v1/auth/otp/send/   → Gửi OTP 6 số đến email
POST /api/v1/auth/otp/verify/ → Xác thực OTP → trả Keycloak tokens
"""

from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework import serializers as drf_serializers
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from common.responses import success_response, error_response
from common.response_codes import ResponseCode
from common import otp as otp_service
from common.keycloak_admin import (
    KeycloakAdminError,
    get_or_create_keycloak_user,
    exchange_token_for_user,
)
from common.authentication import KeycloakJWTAuthentication

# ── Input Serializers ──────────────────────────────────────────────────────────


class OtpSendInputSerializer(drf_serializers.Serializer):
    email = drf_serializers.EmailField()


class OtpVerifyInputSerializer(drf_serializers.Serializer):
    email = drf_serializers.EmailField()
    code = drf_serializers.CharField(min_length=6, max_length=6)


# ── Output Serializer ──────────────────────────────────────────────────────────


class OtpTokenOutputSerializer(drf_serializers.Serializer):
    """
    Token response trả về cho app sau khi OTP verify thành công.
    App dùng access_token cho mọi API call, refresh_token để làm mới session.
    """

    access_token = drf_serializers.CharField()
    refresh_token = drf_serializers.CharField()
    token_type = drf_serializers.CharField()
    expires_in = drf_serializers.IntegerField()
    refresh_expires_in = drf_serializers.IntegerField()


# ── Views ──────────────────────────────────────────────────────────────────────


class OtpSendView(APIView):
    """
    POST /api/v1/auth/otp/send/

    Gửi mã OTP 6 chữ số đến email người dùng.
    - Email chưa đăng ký sẽ được tạo tài khoản tự động khi verify thành công.
    - Cooldown: 60 giây giữa các lần gửi.
    - Không yêu cầu xác thực (AllowAny).
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="Send OTP",
        operation_description="Gửi mã OTP 6 số đến email. Cooldown 60s giữa các lần gửi.",
        request_body=OtpSendInputSerializer,
        responses={
            200: openapi.Response("OTP đã được gửi."),
            429: openapi.Response("Cooldown — vui lòng chờ trước khi gửi lại."),
        },
        tags=["Mobile Auth"],
    )
    def post(self, request):
        serializer = OtpSendInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].strip().lower()

        try:
            otp_service.send_otp(email)
        except otp_service.OtpCooldownError as e:
            return error_response(
                code=ResponseCode.RATE_LIMITED,
                message=str(e),
                errors={"cooldown_remaining": e.remaining_seconds},
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        return success_response(
            message=f"Mã OTP đã được gửi đến {email}.",
            data={"email": email},
        )


class OtpVerifyView(APIView):
    """
    POST /api/v1/auth/otp/verify/

    Xác thực mã OTP và trả về Keycloak tokens.

    Flow:
    1. Verify OTP từ cache.
    2. Lấy hoặc tạo user trong Keycloak (admin API).
    3. Thực hiện Token Exchange → mint Keycloak JWT cho user.
    4. Trả access_token + refresh_token về cho app.

    Lưu ý: access_token là Keycloak JWT hợp lệ — app dùng luôn để gọi API,
    không cần bước đăng nhập thêm.
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="Verify OTP & Get Tokens",
        operation_description=(
            "Xác thực OTP 6 số. Nếu đúng, trả về Keycloak access_token và refresh_token. "
            "App lưu tokens và dùng access_token cho mọi API request tiếp theo."
        ),
        request_body=OtpVerifyInputSerializer,
        responses={
            200: OtpTokenOutputSerializer(),
            400: openapi.Response("OTP sai hoặc hết hạn."),
            429: openapi.Response("Khoá do nhập sai quá nhiều lần."),
            503: openapi.Response("Không kết nối được Keycloak."),
        },
        tags=["Mobile Auth"],
    )
    def post(self, request):
        serializer = OtpVerifyInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].strip().lower()
        code = serializer.validated_data["code"]

        # 1) Verify OTP
        try:
            otp_service.verify_otp(email, code, consume=False)
        except otp_service.OtpExpiredError as e:
            return error_response(
                code=ResponseCode.INVALID_CREDENTIALS,
                message=str(e),
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        except otp_service.OtpMaxAttemptsError as e:
            return error_response(
                code=ResponseCode.RATE_LIMITED,
                message=str(e),
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        except otp_service.OtpInvalidError as e:
            return error_response(
                code=ResponseCode.INVALID_CREDENTIALS,
                message=str(e),
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # 2 + 3) Lấy/tạo user trong Keycloak → Token Exchange
        try:
            keycloak_user_id = get_or_create_keycloak_user(email)
            token_data = exchange_token_for_user(keycloak_user_id)
            KeycloakJWTAuthentication().authenticate_token(token_data["access_token"])
            otp_service.consume_otp(email)
        except KeycloakAdminError as e:
            return error_response(
                code=ResponseCode.SERVICE_UNAVAILABLE,
                message="Không thể hoàn tất đăng nhập. Vui lòng thử lại sau.",
                errors={"detail": str(e)},
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except (AuthenticationFailed, KeyError) as e:
            return error_response(
                code=ResponseCode.INVALID_CREDENTIALS,
                message="Không thể xác thực token sau khi đăng nhập. Vui lòng thử lại.",
                errors={"detail": str(e)},
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        # 4) Trả token cho app
        output = OtpTokenOutputSerializer(
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
            message="Đăng nhập thành công.",
        )
