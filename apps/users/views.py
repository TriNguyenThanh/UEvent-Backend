from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from common import otp as otp_service
from common.keycloak_admin import KeycloakAdminError
from common.response_codes import ResponseCode
from common.responses import error_response, success_response
from apps.users.serializers import (
    ChangeEmailInputSerializer,
    ChangeEmailNewOtpInputSerializer,
    UserProfileOutputSerializer,
    UpdateProfileInputSerializer,
)
from apps.users.services import UserService


class UserProfileEmailOtpView(APIView):
    """POST /api/v1/auth/profile/email/otp/ - gửi OTP đến email hiện tại."""

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Send Email Change OTP",
        operation_description=(
            "Gửi OTP đến email hiện tại của user đang đăng nhập. "
            "Client không truyền email cũ để tránh xác nhận sai tài khoản."
        ),
        responses={
            200: openapi.Response("OTP đã được gửi."),
            429: openapi.Response("Cooldown - vui lòng chờ trước khi gửi lại."),
        },
        tags=["Mobile Auth"],
    )
    def post(self, request):
        try:
            email = UserService.send_email_change_otp(request.user)
        except otp_service.OtpCooldownError as exc:
            return error_response(
                code=ResponseCode.RATE_LIMITED,
                message=str(exc),
                errors={"cooldown_remaining": exc.remaining_seconds},
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        return success_response(
            message=f"Mã OTP xác nhận đổi email đã được gửi đến {email}.",
            data={"email": email},
        )


class UserProfileEmailChangeView(APIView):
    """PATCH /api/v1/auth/profile/email/ - đổi email bằng OTP của email hiện tại."""

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Change My Email",
        operation_description=(
            "Đổi email tài khoản bằng OTP đã gửi đến email hiện tại. "
            "Endpoint này không yêu cầu mật khẩu."
        ),
        request_body=ChangeEmailInputSerializer,
        responses={
            200: UserProfileOutputSerializer(),
            400: openapi.Response("Dữ liệu hoặc OTP không hợp lệ."),
        },
        tags=["Mobile Auth"],
    )
    def patch(self, request):
        input_serializer = ChangeEmailInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        try:
            keycloak_subject = ""
            if isinstance(request.auth, dict):
                keycloak_subject = str(request.auth.get("sub") or "")
            user = UserService.change_email_with_otp(
                request.user,
                new_email=input_serializer.validated_data["new_email"],
                current_otp_code=input_serializer.validated_data["current_otp_code"],
                new_email_otp_code=input_serializer.validated_data[
                    "new_email_otp_code"
                ],
                keycloak_subject=keycloak_subject,
            )
        except ValidationError as exc:
            return error_response(
                code=ResponseCode.VALIDATION_ERROR,
                message="Không thể cập nhật email.",
                errors=exc.detail,
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        except KeycloakAdminError as exc:
            return error_response(
                code=ResponseCode.SERVICE_UNAVAILABLE,
                message="Không thể đồng bộ email với Keycloak. Vui lòng thử lại sau.",
                errors={"detail": str(exc)},
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        output = UserProfileOutputSerializer(user)
        return success_response(data=output.data, message="Cập nhật email thành công.")


class UserProfileNewEmailOtpView(APIView):
    """POST /api/v1/auth/profile/email/new/otp/ - gửi OTP đến email mới."""

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Send New Email OTP",
        operation_description=(
            "Xác thực OTP của email hiện tại, sau đó gửi OTP đến email mới. "
            "Endpoint này chưa cập nhật email."
        ),
        request_body=ChangeEmailNewOtpInputSerializer,
        responses={
            200: openapi.Response("OTP đã được gửi đến email mới."),
            400: openapi.Response("Dữ liệu hoặc OTP email hiện tại không hợp lệ."),
            429: openapi.Response("Cooldown - vui lòng chờ trước khi gửi lại."),
        },
        tags=["Mobile Auth"],
    )
    def post(self, request):
        input_serializer = ChangeEmailNewOtpInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        try:
            email = UserService.send_new_email_change_otp(
                request.user,
                new_email=input_serializer.validated_data["new_email"],
                current_otp_code=input_serializer.validated_data["current_otp_code"],
            )
        except ValidationError as exc:
            return error_response(
                code=ResponseCode.VALIDATION_ERROR,
                message="Không thể xác nhận email mới.",
                errors=exc.detail,
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        except otp_service.OtpCooldownError as exc:
            return error_response(
                code=ResponseCode.RATE_LIMITED,
                message=str(exc),
                errors={"cooldown_remaining": exc.remaining_seconds},
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        return success_response(
            message=f"Mã OTP xác nhận đã được gửi đến {email}.",
            data={"email": email},
        )


class UserProfileView(APIView):
    """
    GET  /api/v1/auth/profile — lấy thông tin user hiện tại.
    PATCH /api/v1/auth/profile — cập nhật profile.
    """

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Get My Profile",
        operation_description="Trả về thông tin profile của user đang đăng nhập.",
        responses={200: UserProfileOutputSerializer()},
        tags=["Mobile Auth"],
    )
    def get(self, request):
        user = UserService.ensure_avatar_url(request.user)
        serializer = UserProfileOutputSerializer(user)
        return success_response(data=serializer.data, message="Lấy profile thành công.")

    @swagger_auto_schema(
        operation_summary="Update My Profile",
        operation_description="Cập nhật thông tin profile của user đang đăng nhập.",
        request_body=UpdateProfileInputSerializer,
        responses={200: UserProfileOutputSerializer()},
        tags=["Mobile Auth"],
    )
    def patch(self, request):
        input_serializer = UpdateProfileInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        user = UserService.update_profile(request.user, input_serializer.validated_data)
        output = UserProfileOutputSerializer(user)
        return success_response(
            data=output.data, message="Cập nhật profile thành công."
        )
