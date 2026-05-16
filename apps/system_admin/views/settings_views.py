from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from common.responses import success_response

from ..permissions import IsAdminOrSuperUser
from ..serializers.common_serializers import AdminErrorResponseSerializer
from ..serializers.response_serializers import AdminSettingsEnvelopeResponseSerializer
from ..serializers.settings_serializers import AdminSettingsOutputSerializer, AdminSettingsUpdateInputSerializer
from ..services.settings_services import AdminSettingsService


ADMIN_SETTINGS_ERROR_RESPONSES = {
    400: AdminErrorResponseSerializer(),
    401: AdminErrorResponseSerializer(),
    403: AdminErrorResponseSerializer(),
}


class AdminSettingsView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]

    @swagger_auto_schema(
        operation_summary="List Admin Settings",
        responses={200: AdminSettingsEnvelopeResponseSerializer(), **ADMIN_SETTINGS_ERROR_RESPONSES},
        tags=["Admin Settings"],
    )
    def get(self, request):
        data = AdminSettingsService.list_settings(group=request.query_params.get("group"))
        return success_response(
            data=AdminSettingsOutputSerializer(data).data,
            message="Lấy cấu hình hệ thống thành công.",
        )

    @swagger_auto_schema(
        operation_summary="Update Admin Settings",
        request_body=AdminSettingsUpdateInputSerializer,
        responses={200: AdminSettingsEnvelopeResponseSerializer(), **ADMIN_SETTINGS_ERROR_RESPONSES},
        tags=["Admin Settings"],
    )
    def patch(self, request):
        serializer = AdminSettingsUpdateInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = AdminSettingsService.update_settings(actor=request.user, **serializer.to_service_data())
        return success_response(
            data=AdminSettingsOutputSerializer(data).data,
            message="Cập nhật cấu hình hệ thống thành công.",
        )
