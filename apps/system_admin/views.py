from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from drf_yasg.utils import swagger_auto_schema

from apps.users.models import User
from common.exceptions import ValidationError, NotFoundError
from .services import AdminUserService
from .serializers import (
    AdminUserListOutputSerializer,
    AdminUserDetailOutputSerializer,
    AdminUpdateUserInputSerializer,
    AdminBanUserInputSerializer,
    AdminUnbanUserInputSerializer,
    AdminAssignRoleInputSerializer,
)

class AdminUserListView(generics.ListAPIView):
    """
    Danh sách user với advanced filtering, searching, và sorting.
    """
    serializer_class = AdminUserListOutputSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['username', 'email', 'full_name', 'student_code']
    filterset_fields = ['account_status', 'faculty', 'is_active']
    ordering_fields = ['created_at', 'username', 'email']


    def get_queryset(self):
        return AdminUserService.list_users()


class AdminUserDetailUpdateDeleteView(APIView):
    """
    Retrieves, updates, or soft-deletes a user.
    """

    @swagger_auto_schema(responses={200: AdminUserDetailOutputSerializer()})
    def get(self, request, pk):
        user = AdminUserService.get_user(pk)
        data = AdminUserDetailOutputSerializer(user).data
        return Response(data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        request_body=AdminUpdateUserInputSerializer,
        responses={200: AdminUserDetailOutputSerializer()}
    )
    def patch(self, request, pk):
        serializer = AdminUpdateUserInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = AdminUserService.update_user(
            actor=request.user,
            user_id=pk,
            data=serializer.to_service_data()
        )
        return Response(AdminUserDetailOutputSerializer(user).data)

    def delete(self, request, pk):
        AdminUserService.soft_delete_user(
            actor=request.user,
            target_user_id=pk,
            reason=request.data.get('reason', '')
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminBanUserView(APIView):
    """
    Ban a user.
    """
    @swagger_auto_schema(
        request_body=AdminBanUserInputSerializer,
        responses={200: AdminUserDetailOutputSerializer()}
    )
    def post(self, request, pk):
        serializer = AdminBanUserInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = AdminUserService.ban_user(
            actor=request.user,
            target_user_id=pk,
            **serializer.to_service_data()
        )
        return Response(AdminUserDetailOutputSerializer(user).data)


class AdminUnbanUserView(APIView):
    """
    Unban a user.
    """
    @swagger_auto_schema(
        request_body=AdminUnbanUserInputSerializer,
        responses={200: AdminUserDetailOutputSerializer()}
    )
    def post(self, request, pk):
        serializer = AdminUnbanUserInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = AdminUserService.unban_user(
            actor=request.user,
            target_user_id=pk,
            **serializer.to_service_data()
        )
        return Response(AdminUserDetailOutputSerializer(user).data)


class AdminRestoreUserView(APIView):
    """
    Restore a soft-deleted user.
    """
    @swagger_auto_schema(responses={200: AdminUserDetailOutputSerializer()})
    def post(self, request, pk):
        user = AdminUserService.restore_user(
            actor=request.user,
            target_user_id=pk
        )
        return Response(AdminUserDetailOutputSerializer(user).data)


class AdminAssignRoleView(APIView):
    """
    Assign a role to a user.
    """
    @swagger_auto_schema(
        request_body=AdminAssignRoleInputSerializer,
        responses={200: AdminUserDetailOutputSerializer()}
    )
    def post(self, request, pk):
        serializer = AdminAssignRoleInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = AdminUserService.assign_role(
            actor=request.user,
            target_user_id=pk,
            **serializer.to_service_data()
        )
        return Response(AdminUserDetailOutputSerializer(user).data)


class AdminRemoveRoleView(APIView):
    """
    Remove a role from a user.
    """
    @swagger_auto_schema(responses={200: AdminUserDetailOutputSerializer()})
    def delete(self, request, pk, role_code):
        user = AdminUserService.remove_role(
            actor=request.user,
            target_user_id=pk,
            role_code=role_code
        )
        return Response(AdminUserDetailOutputSerializer(user).data)
