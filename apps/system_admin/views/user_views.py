from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from drf_yasg.utils import swagger_auto_schema

from common.responses import created_response, deleted_response, success_response
from ..pagination import AdminStandardPagination
from ..permissions import IsAdminOrSuperUser
from ..services.user_services import AdminUserService
from ..serializers.common_serializers import AdminErrorResponseSerializer
from ..serializers.response_serializers import (
    AdminUserEnvelopeResponseSerializer,
    AdminUserListEnvelopeResponseSerializer,
    AdminUserStatisticsEnvelopeResponseSerializer,
)
from ..serializers.user_serializers import (
    AdminUserListOutputSerializer,
    AdminUserDetailOutputSerializer,
    AdminCreateUserInputSerializer,
    AdminUpdateUserInputSerializer,
    AdminBanUserInputSerializer,
    AdminUnbanUserInputSerializer,
    AdminAssignRoleInputSerializer,
    UserStatisticsOutputSerializer,
)


ADMIN_USER_ERROR_RESPONSES = {
    400: AdminErrorResponseSerializer(),
    401: AdminErrorResponseSerializer(),
    403: AdminErrorResponseSerializer(),
    404: AdminErrorResponseSerializer(),
}


class AdminUserListView(generics.ListAPIView):
    """
    Danh sách user với advanced filtering, searching, sorting và tạo user mới.
    """
    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]
    serializer_class = AdminUserListOutputSerializer
    pagination_class = AdminStandardPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['username', 'email', 'full_name', 'student_code']
    filterset_fields = ['account_status', 'faculty', 'is_active']
    ordering_fields = ['created_at', 'username', 'email']

    def get_queryset(self):
        return AdminUserService.list_users()

    @swagger_auto_schema(
        operation_summary="List Admin Users",
        operation_description="Lấy danh sách user với phân trang, tìm kiếm, lọc và sắp xếp.",
        responses={200: AdminUserListEnvelopeResponseSerializer(), **ADMIN_USER_ERROR_RESPONSES},
        tags=["Admin User Management"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class AdminUserCreateView(APIView):

    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]

    @swagger_auto_schema(
        operation_summary="Create Admin User",
        operation_description="Tạo user mới và gán role theo danh sách role_codes nếu có.",
        request_body=AdminCreateUserInputSerializer,
        responses={201: AdminUserEnvelopeResponseSerializer(), **ADMIN_USER_ERROR_RESPONSES},
        tags=["Admin User Management"],
    )
    def post(self, request):
        serializer = AdminCreateUserInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = AdminUserService.create_user(
            actor=request.user,
            data=serializer.to_service_data(),
        )
        return created_response(
            data=AdminUserDetailOutputSerializer(user).data,
            message="Tạo người dùng thành công.",
        )


class AdminUserDetailUpdateDeleteView(APIView):
    """
    Retrieves, updates, or soft-deletes a user.
    """
    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]

    @swagger_auto_schema(responses={200: AdminUserEnvelopeResponseSerializer(), **ADMIN_USER_ERROR_RESPONSES})
    def get(self, request, pk):
        user = AdminUserService.get_user(pk)
        data = AdminUserDetailOutputSerializer(user).data
        return success_response(data=data, message="Lấy thông tin người dùng thành công.")

    @swagger_auto_schema(
        request_body=AdminUpdateUserInputSerializer,
        responses={200: AdminUserEnvelopeResponseSerializer(), **ADMIN_USER_ERROR_RESPONSES}
    )
    def patch(self, request, pk):
        user = AdminUserService.get_user(pk)
        serializer = AdminUpdateUserInputSerializer(instance=user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        user = AdminUserService.update_user(
            actor=request.user,
            user_id=pk,
            data=serializer.to_service_data()
        )
        return success_response(
            data=AdminUserDetailOutputSerializer(user).data,
            message="Cập nhật người dùng thành công.",
        )

    def delete(self, request, pk):
        AdminUserService.soft_delete_user(
            actor=request.user,
            target_user_id=pk,
            reason=request.data.get('reason', '')
        )
        return deleted_response(message="Xóa mềm người dùng thành công.")


class AdminBanUserView(APIView):
    """
    Ban a user.
    """
    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]
    @swagger_auto_schema(
        request_body=AdminBanUserInputSerializer,
        responses={200: AdminUserEnvelopeResponseSerializer(), **ADMIN_USER_ERROR_RESPONSES}
    )
    def post(self, request, pk):
        serializer = AdminBanUserInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = AdminUserService.ban_user(
            actor=request.user,
            target_user_id=pk,
            **serializer.to_service_data()
        )
        return success_response(
            data=AdminUserDetailOutputSerializer(user).data,
            message="Khóa người dùng thành công.",
        )


class AdminUnbanUserView(APIView):
    """
    Unban a user.
    """
    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]
    @swagger_auto_schema(
        request_body=AdminUnbanUserInputSerializer,
        responses={200: AdminUserEnvelopeResponseSerializer(), **ADMIN_USER_ERROR_RESPONSES}
    )
    def post(self, request, pk):
        serializer = AdminUnbanUserInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = AdminUserService.unban_user(
            actor=request.user,
            target_user_id=pk,
            **serializer.to_service_data()
        )
        return success_response(
            data=AdminUserDetailOutputSerializer(user).data,
            message="Mở khóa người dùng thành công.",
        )


class AdminRestoreUserView(APIView):
    """
    Restore a soft-deleted user.
    """
    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]
    @swagger_auto_schema(responses={200: AdminUserEnvelopeResponseSerializer(), **ADMIN_USER_ERROR_RESPONSES})
    def post(self, request, pk):
        user = AdminUserService.restore_user(
            actor=request.user,
            target_user_id=pk
        )
        return success_response(
            data=AdminUserDetailOutputSerializer(user).data,
            message="Khôi phục người dùng thành công.",
        )


class AdminAssignRoleView(APIView):
    """
    Assign a role to a user.
    """
    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]
    @swagger_auto_schema(
        request_body=AdminAssignRoleInputSerializer,
        responses={200: AdminUserEnvelopeResponseSerializer(), **ADMIN_USER_ERROR_RESPONSES}
    )
    def post(self, request, pk):
        serializer = AdminAssignRoleInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = AdminUserService.assign_role(
            actor=request.user,
            target_user_id=pk,
            **serializer.to_service_data()
        )
        return success_response(
            data=AdminUserDetailOutputSerializer(user).data,
            message="Gán vai trò người dùng thành công.",
        )


class AdminRemoveRoleView(APIView):
    """
    Remove a role from a user.
    """
    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]
    @swagger_auto_schema(responses={200: AdminUserEnvelopeResponseSerializer(), **ADMIN_USER_ERROR_RESPONSES})
    def delete(self, request, pk, role_code):
        user = AdminUserService.remove_role(
            actor=request.user,
            target_user_id=pk,
            role_code=role_code
        )
        return success_response(
            data=AdminUserDetailOutputSerializer(user).data,
            message="Gỡ vai trò người dùng thành công.",
        )


class AdminUserStatisticsView(APIView):
    """
    Thống kê tổng quan về user cho Admin Dashboard.
    """
    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]

    @swagger_auto_schema(
        operation_summary="User Statistics",
        operation_description="Thống kê tổng số user, phân bổ theo status/faculty/role, và biểu đồ user mới 30 ngày.",
        responses={200: AdminUserStatisticsEnvelopeResponseSerializer(), **ADMIN_USER_ERROR_RESPONSES},
        tags=["Admin User Management"],
    )
    def get(self, request):
        data = AdminUserService.get_user_statistics()
        output = UserStatisticsOutputSerializer(data)
        return success_response(data=output.data, message="Lấy thống kê người dùng thành công.")
