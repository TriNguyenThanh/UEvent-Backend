from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
# pyrefly: ignore [missing-import]
from drf_yasg.utils import swagger_auto_schema

from common.responses import success_response
from ..permissions import IsAdminOrSuperUser
from ..serializers.auth_serializer import (
    AdminLoginInputSerializer,
    AdminLoginOutputSerializer,
    AdminLogoutInputSerializer,
    AdminTokenRefreshInputSerializer,
    AdminTokenRefreshOutputSerializer,
    AdminUserInfoOutputSerializer,
)
from ..services.auth_service import AdminAuthService


class AdminLoginView(APIView):
    """Endpoint đăng nhập admin: backend đổi username/password lấy token Keycloak."""

    permission_classes = [AllowAny]
    authentication_classes = []

    @swagger_auto_schema(
        operation_summary="Admin Login",
        operation_description="Xác thực admin qua Keycloak và trả về access/refresh token.",
        request_body=AdminLoginInputSerializer,
        responses={200: AdminLoginOutputSerializer()},
        tags=["Admin Auth"],
    )
    def post(self, request):
        serializer = AdminLoginInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = AdminAuthService.admin_login(
            username=serializer.validated_data["username"],
            password=serializer.validated_data["password"],
        )
        output = AdminLoginOutputSerializer(result)
        return success_response(data=output.data, message="Đăng nhập quản trị viên thành công.")


class AdminTokenRefreshView(APIView):
    """Endpoint làm mới Keycloak access token bằng refresh token."""

    permission_classes = [AllowAny]
    authentication_classes = []

    @swagger_auto_schema(
        operation_summary="Admin Token Refresh",
        operation_description="Gửi Keycloak refresh token để nhận access token mới.",
        request_body=AdminTokenRefreshInputSerializer,
        responses={200: AdminTokenRefreshOutputSerializer()},
        tags=["Admin Auth"],
    )
    def post(self, request):
        serializer = AdminTokenRefreshInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = AdminAuthService.refresh_token(refresh=serializer.validated_data["refresh"])
        output = AdminTokenRefreshOutputSerializer(result)
        return success_response(data=output.data, message="Làm mới access token thành công.")


class AdminLogoutView(APIView):
    """Endpoint đăng xuất admin, thu hồi refresh token Keycloak nếu có."""

    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]

    @swagger_auto_schema(
        operation_summary="Admin Logout",
        operation_description="Ghi audit logout và thu hồi Keycloak refresh token nếu client gửi kèm.",
        request_body=AdminLogoutInputSerializer,
        responses={200: "Đăng xuất thành công."},
        tags=["Admin Auth"],
    )
    def post(self, request):
        serializer = AdminLogoutInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        AdminAuthService.admin_logout(
            actor=request.user,
            refresh=serializer.validated_data.get("refresh") or None,
        )
        return success_response(data=None, message="Đăng xuất quản trị viên thành công.")


class AdminMeView(APIView):
    """
    Endpoint xác thực JWT Token và trả về thông tin admin hiện tại.
    Client gửi header `Authorization: Bearer <access_token>`.
    Nếu token hợp lệ thì trả về thông tin user. Nếu không thì trả về 401.
    """

    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]

    @swagger_auto_schema(
        operation_summary="Get Current Admin Info",
        operation_description="Xác thực JWT token trong header và trả về thông tin quản trị viên hiện tại.",
        responses={
            200: AdminUserInfoOutputSerializer(),
            401: "Token không hợp lệ hoặc đã hết hạn.",
            403: "Không có quyền admin.",
        },
        tags=["Admin Auth"],
    )
    def get(self, request):
        user = request.user
        data = AdminUserInfoOutputSerializer({
            "id": str(user.pk),
            "username": user.username,
            "full_name": user.full_name,
            "email": user.email,
            "avatar_url": user.avatar_url,
            "is_superuser": user.is_superuser,
        }).data
        return success_response(data=data, message="Lấy thông tin quản trị viên thành công.")
