from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from common.responses import created_response, deleted_response, success_response

from ..pagination import AdminStandardPagination
from ..permissions import IsAdminOrSuperUser
from ..serializers.common_serializers import AdminCsvExportResponseSerializer, AdminErrorResponseSerializer
from ..serializers.notification_serializers import (
    AdminNotificationDetailOutputSerializer,
    AdminNotificationInputSerializer,
    AdminNotificationListOutputSerializer,
    AdminNotificationPublishInputSerializer,
    AdminNotificationStatisticsOutputSerializer,
)
from ..serializers.response_serializers import (
    AdminNotificationEnvelopeResponseSerializer,
    AdminNotificationListEnvelopeResponseSerializer,
    AdminNotificationStatisticsEnvelopeResponseSerializer,
)
from ..services.notification_services import AdminNotificationService


ADMIN_NOTIFICATION_ERROR_RESPONSES = {
    400: AdminErrorResponseSerializer(),
    401: AdminErrorResponseSerializer(),
    403: AdminErrorResponseSerializer(),
    404: AdminErrorResponseSerializer(),
}


class AdminNotificationListCreateView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]
    serializer_class = AdminNotificationListOutputSerializer
    pagination_class = AdminStandardPagination
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["title", "message", "created_by__username", "created_by__email"]
    ordering_fields = ["created_at", "scheduled_at", "sent_at", "status", "type"]
    ordering = ["-created_at"]

    def get_queryset(self):
        params = self.request.query_params
        return AdminNotificationService.list_notifications(
            status=params.get("status"),
            notification_type=params.get("type"),
            audience_type=params.get("audience_type"),
        )

    @swagger_auto_schema(
        operation_summary="List Admin Notifications",
        manual_parameters=[
            openapi.Parameter("status", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False),
            openapi.Parameter("type", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False),
            openapi.Parameter("audience_type", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False),
            openapi.Parameter("search", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False),
            openapi.Parameter("ordering", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False),
        ],
        responses={200: AdminNotificationListEnvelopeResponseSerializer(), **ADMIN_NOTIFICATION_ERROR_RESPONSES},
        tags=["Admin Notification Management"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Create Admin Notification",
        request_body=AdminNotificationInputSerializer,
        responses={201: AdminNotificationEnvelopeResponseSerializer(), **ADMIN_NOTIFICATION_ERROR_RESPONSES},
        tags=["Admin Notification Management"],
    )
    def post(self, request):
        serializer = AdminNotificationInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        notification = AdminNotificationService.create_notification(
            actor=request.user,
            data=serializer.to_service_data(),
        )
        return created_response(
            data=AdminNotificationDetailOutputSerializer(notification).data,
            message="Tạo thông báo thành công.",
        )


class AdminNotificationStatisticsView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]

    @swagger_auto_schema(
        operation_summary="Notification Statistics",
        responses={200: AdminNotificationStatisticsEnvelopeResponseSerializer(), **ADMIN_NOTIFICATION_ERROR_RESPONSES},
        tags=["Admin Notification Management"],
    )
    def get(self, request):
        data = AdminNotificationService.get_statistics()
        return success_response(
            data=AdminNotificationStatisticsOutputSerializer(data).data,
            message="Lấy thống kê thông báo thành công.",
        )


class AdminNotificationPaginationConfigView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]

    @swagger_auto_schema(
        operation_summary="Notification Pagination Config",
        responses={200: AdminNotificationEnvelopeResponseSerializer(), **ADMIN_NOTIFICATION_ERROR_RESPONSES},
        tags=["Admin Notification Management"],
    )
    def get(self, request):
        return success_response(
            data={"per_page": 10, "max_visible_pages": 5},
            message="Lấy cấu hình phân trang thông báo thành công.",
        )


class AdminNotificationExportView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]

    @swagger_auto_schema(
        operation_summary="Export Admin Notifications",
        manual_parameters=[
            openapi.Parameter("status", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False),
            openapi.Parameter("type", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False),
            openapi.Parameter("audience_type", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False),
            openapi.Parameter("export_format", openapi.IN_QUERY, type=openapi.TYPE_STRING, enum=["csv", "xlsx", "excel"], required=False),
        ],
        responses={200: AdminCsvExportResponseSerializer(), **ADMIN_NOTIFICATION_ERROR_RESPONSES},
        tags=["Admin Notification Management"],
    )
    def get(self, request):
        return AdminNotificationService.export_notifications(
            actor=request.user,
            filters={
                "status": request.query_params.get("status"),
                "type": request.query_params.get("type"),
                "audience_type": request.query_params.get("audience_type"),
            },
            export_format=request.query_params.get("export_format", "csv"),
        )


class AdminNotificationDetailUpdateDeleteView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]

    @swagger_auto_schema(
        operation_summary="Get Admin Notification",
        responses={200: AdminNotificationEnvelopeResponseSerializer(), **ADMIN_NOTIFICATION_ERROR_RESPONSES},
        tags=["Admin Notification Management"],
    )
    def get(self, request, pk):
        notification = AdminNotificationService.get_notification(pk)
        return success_response(
            data=AdminNotificationDetailOutputSerializer(notification).data,
            message="Lấy chi tiết thông báo thành công.",
        )

    @swagger_auto_schema(
        operation_summary="Update Admin Notification",
        request_body=AdminNotificationInputSerializer,
        responses={200: AdminNotificationEnvelopeResponseSerializer(), **ADMIN_NOTIFICATION_ERROR_RESPONSES},
        tags=["Admin Notification Management"],
    )
    def patch(self, request, pk):
        serializer = AdminNotificationInputSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        notification = AdminNotificationService.update_notification(
            actor=request.user,
            notification_id=pk,
            data=serializer.to_service_data(),
        )
        return success_response(
            data=AdminNotificationDetailOutputSerializer(notification).data,
            message="Cập nhật thông báo thành công.",
        )

    @swagger_auto_schema(
        operation_summary="Delete Admin Notification",
        responses={200: AdminNotificationEnvelopeResponseSerializer(), **ADMIN_NOTIFICATION_ERROR_RESPONSES},
        tags=["Admin Notification Management"],
    )
    def delete(self, request, pk):
        AdminNotificationService.delete_notification(
            actor=request.user,
            notification_id=pk,
        )
        return deleted_response(message="Xóa thông báo thành công.")


class AdminNotificationPublishView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]

    @swagger_auto_schema(
        operation_summary="Publish Admin Notification",
        request_body=AdminNotificationPublishInputSerializer,
        responses={200: AdminNotificationEnvelopeResponseSerializer(), **ADMIN_NOTIFICATION_ERROR_RESPONSES},
        tags=["Admin Notification Management"],
    )
    def post(self, request, pk):
        serializer = AdminNotificationPublishInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        notification = AdminNotificationService.publish_notification(
            actor=request.user,
            notification_id=pk,
            **serializer.to_service_data(),
        )
        return success_response(
            data=AdminNotificationDetailOutputSerializer(notification).data,
            message="Đã xếp hàng gửi thông báo.",
        )
