from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema

from ..serializers.auth_serializer import (
    AdminLoginInputSerializer,
    AdminLoginOutputSerializer,
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
