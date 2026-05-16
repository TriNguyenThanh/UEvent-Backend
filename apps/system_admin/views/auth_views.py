from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
# pyrefly: ignore [missing-import]
from drf_yasg.utils import swagger_auto_schema

from common.responses import success_response
from ..permissions import IsAdminOrSuperUser
# from ..serializers.common_serializers import AdminErrorResponseSerializer
# from ..serializers.response_serializers import (
#     AdminLoginEnvelopeResponseSerializer,
#     AdminLogoutEnvelopeResponseSerializer,
#     AdminUserInfoEnvelopeResponseSerializer,
# )
# from ..serializers.auth_serializer import (
#     AdminLoginInputSerializer,
#     AdminLoginOutputSerializer,
#     AdminUserInfoOutputSerializer,
# )
from ..serializers.auth_serializer import AdminUserInfoOutputSerializer
# from ..services.auth_service import AdminAuthService


# ADMIN_AUTH_ERROR_RESPONSES = {
#     400: AdminErrorResponseSerializer(),
#     401: AdminErrorResponseSerializer(),
#     403: AdminErrorResponseSerializer(),
# }
#
#
# class AdminLoginView(APIView):
#     """
#     Endpoint đăng nhập dành cho quản trị viên.
#     Trả về JWT Access & Refresh tokens nếu xác thực thành công.
#     """
#     permission_classes = [AllowAny]
#     authentication_classes = []  # Không yêu cầu auth cho endpoint login
#
#     @swagger_auto_schema(
#         operation_summary="Admin Login",
#         operation_description="Xác thực quản trị viên bằng username/password, trả về JWT tokens.",
#         request_body=AdminLoginInputSerializer,
#         responses={
#             200: AdminLoginEnvelopeResponseSerializer(),
#             **ADMIN_AUTH_ERROR_RESPONSES,
#         },
#         tags=["Admin Auth"],
#     )
#     def post(self, request):
#         serializer = AdminLoginInputSerializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#
#         result = AdminAuthService.admin_login(
#             username=serializer.validated_data['username'],
#             password=serializer.validated_data['password'],
#         )
#
#         output = AdminLoginOutputSerializer(result)
#         return success_response(data=output.data, message="Đăng nhập quản trị viên thành công.")
#
#
# class AdminTokenRefreshView(TokenRefreshView):
#     """
#     Endpoint làm mới JWT Access Token bằng Refresh Token.
#     Client gửi refresh token, nhận lại access token mới.
#     """
#
#     @swagger_auto_schema(
#         operation_summary="Admin Token Refresh",
#         operation_description="Gửi refresh token để nhận access token mới.",
#         request_body=TokenRefreshSerializer,
#         responses={
#             200: AdminLoginEnvelopeResponseSerializer(),
#             **ADMIN_AUTH_ERROR_RESPONSES,
#         },
#         tags=["Admin Auth"],
#     )
#     def post(self, request, *args, **kwargs):
#         serializer = self.get_serializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         return success_response(data=serializer.validated_data, message="Làm mới access token thành công.")
#
#
# class AdminLogoutView(APIView):
#     """
#     Endpoint đăng xuất stateless dành cho quản trị viên.
#     Frontend xóa access/refresh token ở client sau khi gọi thành công.
#     """
#     permission_classes = [IsAuthenticated, IsAdminOrSuperUser]
#
#     @swagger_auto_schema(
#         operation_summary="Admin Logout",
#         operation_description="Ghi audit logout và trả về response thành công. Giai đoạn này chưa revoke refresh token ở server.",
#         responses={
#             200: AdminLogoutEnvelopeResponseSerializer(),
#             **ADMIN_AUTH_ERROR_RESPONSES,
#         },
#         tags=["Admin Auth"],
#     )
#     def post(self, request):
#         AdminAuthService.admin_logout(actor=request.user)
#         return success_response(data=None, message="Đăng xuất quản trị viên thành công.")


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
        return success_response(data=data, message="Lấy thông tin quản trị viên thành công.")

