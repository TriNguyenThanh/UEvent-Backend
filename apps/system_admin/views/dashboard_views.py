from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from common.responses import success_response

from ..permissions import IsAdminOrSuperUser
from ..serializers.common_serializers import AdminErrorResponseSerializer
from ..serializers.dashboard_serializers import (
    AdminDashboardAuditSummarySerializer,
    AdminDashboardGrowthPointSerializer,
    AdminDashboardOverviewSerializer,
    AdminDashboardQueueItemSerializer,
    AdminDashboardStatSerializer,
)
from ..serializers.response_serializers import (
    AdminDashboardAuditSummaryEnvelopeResponseSerializer,
    AdminDashboardGrowthEnvelopeResponseSerializer,
    AdminDashboardOverviewEnvelopeResponseSerializer,
    AdminDashboardQueueEnvelopeResponseSerializer,
    AdminDashboardStatsEnvelopeResponseSerializer,
)
from ..services.dashboard_services import AdminDashboardService


ADMIN_DASHBOARD_ERROR_RESPONSES = {
    401: AdminErrorResponseSerializer(),
    403: AdminErrorResponseSerializer(),
}


class AdminDashboardOverviewView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]

    @swagger_auto_schema(
        operation_summary="Admin Dashboard Overview",
        responses={200: AdminDashboardOverviewEnvelopeResponseSerializer(), **ADMIN_DASHBOARD_ERROR_RESPONSES},
        tags=["Admin Dashboard"],
    )
    def get(self, request):
        data = AdminDashboardService.get_overview()
        return success_response(
            data=AdminDashboardOverviewSerializer(data).data,
            message="Lấy tổng quan bảng điều khiển thành công.",
        )


class AdminDashboardStatsView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]

    @swagger_auto_schema(
        operation_summary="Admin Dashboard Stats",
        responses={200: AdminDashboardStatsEnvelopeResponseSerializer(), **ADMIN_DASHBOARD_ERROR_RESPONSES},
        tags=["Admin Dashboard"],
    )
    def get(self, request):
        data = AdminDashboardService.get_stats()
        return success_response(
            data=AdminDashboardStatSerializer(data, many=True).data,
            message="Lấy chỉ số bảng điều khiển thành công.",
        )


class AdminDashboardGrowthView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]

    @swagger_auto_schema(
        operation_summary="Admin Dashboard Growth",
        responses={200: AdminDashboardGrowthEnvelopeResponseSerializer(), **ADMIN_DASHBOARD_ERROR_RESPONSES},
        tags=["Admin Dashboard"],
    )
    def get(self, request):
        data = AdminDashboardService.get_growth_series()
        return success_response(
            data=AdminDashboardGrowthPointSerializer(data, many=True).data,
            message="Lấy xu hướng tăng trưởng thành công.",
        )


class AdminDashboardQueueView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]

    @swagger_auto_schema(
        operation_summary="Admin Dashboard Queue",
        responses={200: AdminDashboardQueueEnvelopeResponseSerializer(), **ADMIN_DASHBOARD_ERROR_RESPONSES},
        tags=["Admin Dashboard"],
    )
    def get(self, request):
        data = AdminDashboardService.get_queue()
        return success_response(
            data=AdminDashboardQueueItemSerializer(data, many=True).data,
            message="Lấy hàng đợi xử lý thành công.",
        )


class AdminDashboardAuditSummaryView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]

    @swagger_auto_schema(
        operation_summary="Admin Dashboard Audit Summary",
        responses={200: AdminDashboardAuditSummaryEnvelopeResponseSerializer(), **ADMIN_DASHBOARD_ERROR_RESPONSES},
        tags=["Admin Dashboard"],
    )
    def get(self, request):
        data = AdminDashboardService.get_audit_summary()
        return success_response(
            data=AdminDashboardAuditSummarySerializer(data).data,
            message="Lấy tổng quan kiểm toán thành công.",
        )
