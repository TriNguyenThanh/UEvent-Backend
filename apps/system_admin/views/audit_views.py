from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from common.exceptions import ForbiddenError
from common.responses import success_response

from ..permissions import IsAdminOrSuperUser
from ..serializers.audit_serializers import (
    AdminAuditExportQuerySerializer,
    AdminAuditLogOutputSerializer,
    AdminAuditLogQuerySerializer,
    AdminAuditSummaryOutputSerializer,
)
from ..serializers.common_serializers import AdminErrorResponseSerializer
from ..serializers.response_serializers import (
    AdminAuditListEnvelopeResponseSerializer,
    AdminAuditSummaryEnvelopeResponseSerializer,
)
from ..services.audit_log_services import AdminAuditLogService


ADMIN_AUDIT_ERROR_RESPONSES = {
    400: AdminErrorResponseSerializer(),
    401: AdminErrorResponseSerializer(),
    403: AdminErrorResponseSerializer(),
    503: AdminErrorResponseSerializer(),
}


def ensure_audit_permission(user) -> None:
    if getattr(user, "is_superuser", False):
        return

    role_codes = set(
        user.user_roles.filter(deleted_at__isnull=True).values_list("role__code", flat=True)
    )
    if role_codes.intersection({"super_admin", "operations_admin", "audit_admin"}):
        return

    raise ForbiddenError("Chỉ quản trị viên cấp cao hoặc vai trò vận hành mới được xem nhật ký kiểm toán.")


class AdminAuditLogListView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]

    @swagger_auto_schema(
        operation_summary="List Admin Audit Logs",
        manual_parameters=[
            openapi.Parameter("date_from", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False),
            openapi.Parameter("date_to", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False),
            openapi.Parameter("actor_id", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False),
            openapi.Parameter("action_type", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False),
            openapi.Parameter("status", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False),
            openapi.Parameter("page", openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=False),
            openapi.Parameter("page_size", openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=False),
        ],
        responses={200: AdminAuditListEnvelopeResponseSerializer(), **ADMIN_AUDIT_ERROR_RESPONSES},
        tags=["Admin Audit Logs"],
    )
    def get(self, request):
        ensure_audit_permission(request.user)
        serializer = AdminAuditLogQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        result = AdminAuditLogService.search_logs(filters=serializer.to_service_data())
        return success_response(
            data=AdminAuditLogOutputSerializer(result["logs"], many=True).data,
            meta={"pagination": result["pagination"]},
            message="Lấy nhật ký kiểm toán thành công.",
        )


class AdminAuditLogExportView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]

    @swagger_auto_schema(
        operation_summary="Export Admin Audit Logs",
        manual_parameters=[
            openapi.Parameter("date_from", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=True),
            openapi.Parameter("date_to", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=True),
            openapi.Parameter("export_format", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False),
        ],
        responses={200: "CSV/XLSX file", **ADMIN_AUDIT_ERROR_RESPONSES},
        tags=["Admin Audit Logs"],
    )
    def get(self, request):
        ensure_audit_permission(request.user)
        serializer = AdminAuditExportQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return AdminAuditLogService.export_logs(actor=request.user, filters=serializer.to_service_data())


class AdminAuditSummaryView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]

    @swagger_auto_schema(
        operation_summary="Admin Audit Summary",
        responses={200: AdminAuditSummaryEnvelopeResponseSerializer(), **ADMIN_AUDIT_ERROR_RESPONSES},
        tags=["Admin Audit Logs"],
    )
    def get(self, request):
        ensure_audit_permission(request.user)
        data = AdminAuditLogService.get_summary()
        return success_response(
            data=AdminAuditSummaryOutputSerializer(data).data,
            message="Lấy tổng quan nhật ký kiểm toán thành công.",
        )
