from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from drf_yasg.utils import swagger_auto_schema

from ..permissions import IsAdminOrSuperUser
from ..serializers.auth_serializer import (
    AdminLoginInputSerializer,
    AdminLoginOutputSerializer,
    AdminUserInfoOutputSerializer,
)
from ..services.auth_service import AdminAuthService


class AdminLoginView(APIView):
    """
    Endpoint đăng nhập dành cho quản trị viên.
    Trả về JWT Access & Refresh tokens nếu xác thực thành công.
    """
    permission_classes = [AllowAny]
    authentication_classes = []  # Không yêu cầu auth cho endpoint login

    @swagger_auto_schema(
        operation_summary="Admin Login",
        operation_description="Xác thực quản trị viên bằng username/password, trả về JWT tokens.",
        request_body=AdminLoginInputSerializer,
        responses={
            200: AdminLoginOutputSerializer(),
            401: "Thông tin đăng nhập không hợp lệ.",
            403: "Không có quyền truy cập (không phải admin).",
        },
        tags=["Admin Auth"],
    )
    def post(self, request):
        serializer = AdminLoginInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = AdminAuthService.admin_login(
            username=serializer.validated_data['username'],
            password=serializer.validated_data['password'],
        )

        output = AdminLoginOutputSerializer(result)
        return Response(output.data, status=status.HTTP_200_OK)


class AdminTokenRefreshView(TokenRefreshView):
    """
    Endpoint làm mới JWT Access Token bằng Refresh Token.
    Client gửi refresh token, nhận lại access token mới.
    """

    @swagger_auto_schema(
        operation_summary="Admin Token Refresh",
        operation_description="Gửi refresh token để nhận access token mới.",
        request_body=TokenRefreshSerializer,
        tags=["Admin Auth"],
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class AdminMeView(APIView):
    """
    Endpoint xác thực JWT Token và trả về thông tin admin hiện tại.
    Client gửi header `Authorization: Bearer <access_token>`.
    Nếu token hợp lệ → trả về thông tin user. Nếu không → 401.
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
        return Response(data, status=status.HTTP_200_OK)

