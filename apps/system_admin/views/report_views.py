from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from common.responses import success_response

from ..permissions import IsAdminOrSuperUser
from ..serializers.common_serializers import AdminErrorResponseSerializer
from ..serializers.report_serializers import AdminReportOverviewSerializer
from ..services.report_services import AdminReportService


ADMIN_REPORT_ERROR_RESPONSES = {
    401: AdminErrorResponseSerializer(),
    403: AdminErrorResponseSerializer(),
}

REPORT_FILTER_PARAMETERS = [
    openapi.Parameter("from_date", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False),
    openapi.Parameter("to_date", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False),
    openapi.Parameter(
        "group_by",
        openapi.IN_QUERY,
        type=openapi.TYPE_STRING,
        enum=["day", "week", "month"],
        required=False,
    ),
]


class AdminReportOverviewView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]

    @swagger_auto_schema(
        operation_summary="Admin Report Overview",
        manual_parameters=REPORT_FILTER_PARAMETERS,
        responses={200: AdminReportOverviewSerializer(), **ADMIN_REPORT_ERROR_RESPONSES},
        tags=["Admin Reports"],
    )
    def get(self, request):
        data = AdminReportService.get_overview(request.query_params)
        return success_response(
            data=AdminReportOverviewSerializer(data).data,
            message="Lấy báo cáo tổng quan thành công.",
        )


class AdminReportExportView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]

    @swagger_auto_schema(
        operation_summary="Export Admin Reports",
        manual_parameters=[
            *REPORT_FILTER_PARAMETERS,
            openapi.Parameter(
                "report_type",
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                enum=sorted(AdminReportService.REPORT_EXPORT_TYPES),
                required=False,
            ),
            openapi.Parameter(
                "export_format",
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                enum=["csv", "xlsx"],
                required=False,
            ),
        ],
        tags=["Admin Reports"],
    )
    def get(self, request):
        return AdminReportService.build_export_response(
            actor=request.user,
            filters=request.query_params,
        )
