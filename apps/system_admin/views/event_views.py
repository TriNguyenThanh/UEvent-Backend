from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from common.responses import deleted_response, success_response

from ..pagination import AdminStandardPagination
from ..permissions import IsAdminOrSuperUser
from ..serializers.common_serializers import AdminErrorResponseSerializer
from ..serializers.event_serializers import (
    AdminEventDetailOutputSerializer,
    AdminEventListOutputSerializer,
    AdminEventModerationActivitySerializer,
    AdminEventModerationPulseSerializer,
    AdminEventPolicyHandbookSerializer,
    AdminEventStatisticsOutputSerializer,
    AdminEventStatusInputSerializer,
)
from ..serializers.response_serializers import (
    AdminEventEnvelopeResponseSerializer,
    AdminEventListEnvelopeResponseSerializer,
    AdminEventModerationActivitiesEnvelopeResponseSerializer,
    AdminEventModerationPulseEnvelopeResponseSerializer,
    AdminEventPolicyHandbookEnvelopeResponseSerializer,
    AdminEventStatisticsEnvelopeResponseSerializer,
)
from ..services.event_services import AdminEventService


ADMIN_EVENT_ERROR_RESPONSES = {
    400: AdminErrorResponseSerializer(),
    401: AdminErrorResponseSerializer(),
    403: AdminErrorResponseSerializer(),
    404: AdminErrorResponseSerializer(),
}


class AdminEventListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]
    serializer_class = AdminEventListOutputSerializer
    pagination_class = AdminStandardPagination
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["title", "description", "created_by__username", "created_by__email"]
    ordering_fields = ["start_at", "created_at", "status"]
    ordering = ["-start_at", "-created_at"]

    def get_queryset(self):
        params = self.request.query_params
        return AdminEventService.list_events(
            status=params.get("status"),
            category_id=params.get("category"),
            visibility=params.get("visibility"),
            reported=params.get("reported"),
        )

    @swagger_auto_schema(
        operation_summary="List Admin Events",
        manual_parameters=[
            openapi.Parameter("status", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False),
            openapi.Parameter("reported", openapi.IN_QUERY, type=openapi.TYPE_BOOLEAN, required=False),
            openapi.Parameter("category", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False),
            openapi.Parameter("visibility", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False),
            openapi.Parameter("search", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False),
            openapi.Parameter("ordering", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False),
        ],
        responses={200: AdminEventListEnvelopeResponseSerializer(), **ADMIN_EVENT_ERROR_RESPONSES},
        tags=["Admin Event Management"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class AdminEventStatisticsView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]

    @swagger_auto_schema(
        operation_summary="Event Statistics",
        responses={200: AdminEventStatisticsEnvelopeResponseSerializer(), **ADMIN_EVENT_ERROR_RESPONSES},
        tags=["Admin Event Management"],
    )
    def get(self, request):
        data = AdminEventService.get_event_statistics()
        return success_response(
            data=AdminEventStatisticsOutputSerializer(data).data,
            message="Lấy thống kê sự kiện thành công.",
        )


class AdminEventModerationPulseView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]

    @swagger_auto_schema(
        operation_summary="Event Moderation Pulse",
        responses={200: AdminEventModerationPulseEnvelopeResponseSerializer(), **ADMIN_EVENT_ERROR_RESPONSES},
        tags=["Admin Event Management"],
    )
    def get(self, request):
        data = AdminEventService.get_moderation_pulse()
        return success_response(
            data=AdminEventModerationPulseSerializer(data).data,
            message="Lấy nhịp kiểm duyệt sự kiện thành công.",
        )


class AdminEventModerationActivitiesView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]

    @swagger_auto_schema(
        operation_summary="Event Moderation Activities",
        responses={200: AdminEventModerationActivitiesEnvelopeResponseSerializer(), **ADMIN_EVENT_ERROR_RESPONSES},
        tags=["Admin Event Management"],
    )
    def get(self, request):
        data = AdminEventService.get_moderation_activities()
        return success_response(
            data=AdminEventModerationActivitySerializer(data, many=True).data,
            message="Lấy hoạt động kiểm duyệt sự kiện thành công.",
        )


class AdminEventPolicyHandbookView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]

    @swagger_auto_schema(
        operation_summary="Event Policy Handbook",
        responses={200: AdminEventPolicyHandbookEnvelopeResponseSerializer(), **ADMIN_EVENT_ERROR_RESPONSES},
        tags=["Admin Event Management"],
    )
    def get(self, request):
        data = AdminEventService.get_policy_handbook()
        return success_response(
            data=AdminEventPolicyHandbookSerializer(data).data,
            message="Lấy sổ tay chính sách sự kiện thành công.",
        )


class AdminEventDetailDeleteView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]

    @swagger_auto_schema(
        operation_summary="Get Admin Event",
        responses={200: AdminEventEnvelopeResponseSerializer(), **ADMIN_EVENT_ERROR_RESPONSES},
        tags=["Admin Event Management"],
    )
    def get(self, request, pk):
        event = AdminEventService.get_event(pk)
        return success_response(
            data=AdminEventDetailOutputSerializer(event).data,
            message="Lấy thông tin sự kiện thành công.",
        )

    @swagger_auto_schema(
        operation_summary="Delete Admin Event",
        responses={200: AdminEventEnvelopeResponseSerializer(), **ADMIN_EVENT_ERROR_RESPONSES},
        tags=["Admin Event Management"],
    )
    def delete(self, request, pk):
        AdminEventService.delete_event(
            actor=request.user,
            event_id=pk,
            reason=request.data.get("reason", ""),
        )
        return deleted_response(message="Xóa mềm sự kiện thành công.")


class AdminEventStatusView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]

    @swagger_auto_schema(
        operation_summary="Update Event Moderation Status",
        request_body=AdminEventStatusInputSerializer,
        responses={200: AdminEventEnvelopeResponseSerializer(), **ADMIN_EVENT_ERROR_RESPONSES},
        tags=["Admin Event Management"],
    )
    def patch(self, request, pk):
        serializer = AdminEventStatusInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        event = AdminEventService.update_event_status(
            actor=request.user,
            event_id=pk,
            **serializer.to_service_data(),
        )
        return success_response(
            data=AdminEventDetailOutputSerializer(event).data,
            message="Cập nhật trạng thái kiểm duyệt sự kiện thành công.",
        )
