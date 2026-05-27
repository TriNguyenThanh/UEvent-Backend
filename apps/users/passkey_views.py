from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from apps.users.passkey_services import (
    PasskeyConfigurationError,
    PasskeyService,
)
from apps.users.serializers import (
    PasskeyAuthenticationOptionsInputSerializer,
    PasskeyAuthenticationOptionsOutputSerializer,
    PasskeyAuthenticationVerifyInputSerializer,
    PasskeyCredentialOutputSerializer,
    PasskeyRegistrationOptionsOutputSerializer,
    PasskeyRegistrationVerifyInputSerializer,
)
from common.keycloak_admin import KeycloakAdminError
from common.response_codes import ResponseCode
from common.responses import deleted_response, error_response, success_response


class PasskeyRegistrationOptionsView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Begin Passkey Registration",
        operation_description="Tạo WebAuthn challenge để user đang đăng nhập đăng ký passkey.",
        responses={200: PasskeyRegistrationOptionsOutputSerializer()},
        tags=["Mobile Auth"],
    )
    def post(self, request):
        try:
            payload = PasskeyService.begin_registration(request.user)
        except PasskeyConfigurationError as exc:
            return error_response(
                code=ResponseCode.SERVICE_UNAVAILABLE,
                message="Passkey chưa được cấu hình trên server.",
                errors={"detail": str(exc)},
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return success_response(
            data=PasskeyRegistrationOptionsOutputSerializer(payload).data,
            message="Đã tạo challenge đăng ký passkey.",
        )


class PasskeyRegistrationVerifyView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Verify Passkey Registration",
        operation_description="Xác minh attestation WebAuthn và lưu public key credential.",
        request_body=PasskeyRegistrationVerifyInputSerializer,
        responses={200: PasskeyCredentialOutputSerializer()},
        tags=["Mobile Auth"],
    )
    def post(self, request):
        serializer = PasskeyRegistrationVerifyInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            credential = PasskeyService.verify_registration(
                user=request.user,
                challenge_id=str(serializer.validated_data["challenge_id"]),
                credential=serializer.validated_data["credential"],
                device_name=serializer.validated_data.get("device_name", ""),
            )
        except ValidationError as exc:
            return error_response(
                code=ResponseCode.VALIDATION_ERROR,
                message="Không thể đăng ký passkey.",
                errors=exc.detail,
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        except PasskeyConfigurationError as exc:
            return error_response(
                code=ResponseCode.SERVICE_UNAVAILABLE,
                message="Passkey chưa được cấu hình trên server.",
                errors={"detail": str(exc)},
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return success_response(
            data=PasskeyCredentialOutputSerializer(credential).data,
            message="Đăng ký passkey thành công.",
        )


class PasskeyCredentialListView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="List My Passkeys",
        responses={200: PasskeyCredentialOutputSerializer(many=True)},
        tags=["Mobile Auth"],
    )
    def get(self, request):
        credentials = request.user.passkey_credentials.filter(
            revoked_at__isnull=True,
        )
        return success_response(
            data=PasskeyCredentialOutputSerializer(credentials, many=True).data,
            message="Lấy danh sách passkey thành công.",
        )


class PasskeyCredentialRevokeView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Revoke My Passkey",
        responses={200: openapi.Response("Passkey đã được thu hồi.")},
        tags=["Mobile Auth"],
    )
    def delete(self, request, credential_id):
        try:
            PasskeyService.revoke_credential(
                user=request.user,
                credential_id=str(credential_id),
            )
        except ValidationError as exc:
            return error_response(
                code=ResponseCode.NOT_FOUND,
                message="Không tìm thấy passkey.",
                errors=exc.detail,
                status_code=status.HTTP_404_NOT_FOUND,
            )
        return deleted_response(message="Đã thu hồi passkey.")


class PasskeyAuthenticationOptionsView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="Begin Passkey Authentication",
        request_body=PasskeyAuthenticationOptionsInputSerializer,
        responses={200: PasskeyAuthenticationOptionsOutputSerializer()},
        tags=["Mobile Auth"],
    )
    def post(self, request):
        serializer = PasskeyAuthenticationOptionsInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            payload = PasskeyService.begin_authentication(
                serializer.validated_data["email"],
            )
        except PasskeyConfigurationError as exc:
            return error_response(
                code=ResponseCode.SERVICE_UNAVAILABLE,
                message="Passkey chưa được cấu hình trên server.",
                errors={"detail": str(exc)},
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return success_response(
            data=PasskeyAuthenticationOptionsOutputSerializer(payload).data,
            message="Đã tạo challenge đăng nhập passkey.",
        )


class PasskeyAuthenticationVerifyView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="Verify Passkey Authentication",
        request_body=PasskeyAuthenticationVerifyInputSerializer,
        tags=["Mobile Auth"],
    )
    def post(self, request):
        serializer = PasskeyAuthenticationVerifyInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = PasskeyService.verify_authentication(
                email=serializer.validated_data["email"],
                challenge_id=str(serializer.validated_data["challenge_id"]),
                credential=serializer.validated_data["credential"],
            )
        except ValidationError as exc:
            return error_response(
                code=ResponseCode.INVALID_CREDENTIALS,
                message="Không thể xác thực passkey.",
                errors=exc.detail,
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        except PasskeyConfigurationError as exc:
            return error_response(
                code=ResponseCode.SERVICE_UNAVAILABLE,
                message="Passkey chưa được cấu hình trên server.",
                errors={"detail": str(exc)},
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except KeycloakAdminError as exc:
            return error_response(
                code=ResponseCode.SERVICE_UNAVAILABLE,
                message="Không thể phát token đăng nhập. Vui lòng thử lại sau.",
                errors={"detail": str(exc)},
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except (AuthenticationFailed, KeyError) as exc:
            return error_response(
                code=ResponseCode.INVALID_CREDENTIALS,
                message="Không thể xác thực token sau khi đăng nhập passkey.",
                errors={"detail": str(exc)},
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        return success_response(
            data={
                "access_token": result.token_data["access_token"],
                "refresh_token": result.token_data.get("refresh_token", ""),
                "token_type": result.token_data.get("token_type", "Bearer"),
                "expires_in": result.token_data.get("expires_in", 300),
                "refresh_expires_in": result.token_data.get(
                    "refresh_expires_in",
                    1800,
                ),
            },
            message="Đăng nhập passkey thành công.",
        )
