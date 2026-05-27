from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from common.responses import success_response

from ..pagination import AdminStandardPagination
from ..permissions import IsAdminOrSuperUser
from ..serializers.common_serializers import AdminCsvExportResponseSerializer, AdminErrorResponseSerializer
from ..serializers.response_serializers import (
    AdminCheckinLogListEnvelopeResponseSerializer,
    AdminTicketEnvelopeResponseSerializer,
    AdminTicketListEnvelopeResponseSerializer,
    AdminTicketScanEnvelopeResponseSerializer,
    AdminTicketStatisticsEnvelopeResponseSerializer,
)
from ..serializers.ticket_serializers import (
    AdminCheckinLogOutputSerializer,
    AdminTicketCancelInputSerializer,
    AdminTicketOutputSerializer,
    AdminTicketScanInputSerializer,
    AdminTicketScanResultSerializer,
    AdminTicketStatisticsOutputSerializer,
)
from ..services.ticket_services import AdminTicketService


ADMIN_TICKET_ERROR_RESPONSES = {
    400: AdminErrorResponseSerializer(),
    401: AdminErrorResponseSerializer(),
    403: AdminErrorResponseSerializer(),
    404: AdminErrorResponseSerializer(),
}


class AdminTicketListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]
    serializer_class = AdminTicketOutputSerializer
    pagination_class = AdminStandardPagination
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = [
        "ticket_code",
        "registration__user__username",
        "registration__user__email",
        "registration__user__full_name",
        "registration__event__title",
    ]
    ordering_fields = ["created_at", "updated_at", "status", "used_at", "expires_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        params = self.request.query_params
        return AdminTicketService.list_tickets(
            status=params.get("status"),
            event_id=params.get("event_id"),
            user_id=params.get("user_id"),
            search=params.get("search"),
            date_from=params.get("date_from"),
            date_to=params.get("date_to"),
            ordering=params.get("ordering"),
        )

    @swagger_auto_schema(
        operation_summary="List Admin Tickets",
        manual_parameters=[
            openapi.Parameter("status", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False),
            openapi.Parameter("event_id", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False),
            openapi.Parameter("user_id", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False),
            openapi.Parameter("search", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False),
            openapi.Parameter("date_from", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False),
            openapi.Parameter("date_to", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False),
            openapi.Parameter("ordering", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False),
        ],
        responses={200: AdminTicketListEnvelopeResponseSerializer(), **ADMIN_TICKET_ERROR_RESPONSES},
        tags=["Admin Ticket Management"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class AdminTicketDetailView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]

    @swagger_auto_schema(
        operation_summary="Get Admin Ticket",
        responses={200: AdminTicketEnvelopeResponseSerializer(), **ADMIN_TICKET_ERROR_RESPONSES},
        tags=["Admin Ticket Management"],
    )
    def get(self, request, pk):
        ticket = AdminTicketService.get_ticket(pk)
        return success_response(
            data=AdminTicketOutputSerializer(ticket).data,
            message="Lấy chi tiết vé thành công.",
        )


class AdminTicketStatisticsView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]

    @swagger_auto_schema(
        operation_summary="Ticket Statistics",
        responses={200: AdminTicketStatisticsEnvelopeResponseSerializer(), **ADMIN_TICKET_ERROR_RESPONSES},
        tags=["Admin Ticket Management"],
    )
    def get(self, request):
        data = AdminTicketService.get_statistics()
        return success_response(
            data=AdminTicketStatisticsOutputSerializer(data).data,
            message="Lấy thống kê vé thành công.",
        )


class AdminTicketCancelView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]

    @swagger_auto_schema(
        operation_summary="Cancel Admin Ticket",
        request_body=AdminTicketCancelInputSerializer,
        responses={200: AdminTicketEnvelopeResponseSerializer(), **ADMIN_TICKET_ERROR_RESPONSES},
        tags=["Admin Ticket Management"],
    )
    def post(self, request, pk):
        serializer = AdminTicketCancelInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ticket = AdminTicketService.cancel_ticket(
            actor=request.user,
            ticket_id=pk,
            reason=serializer.validated_data.get("reason", ""),
        )
        return success_response(
            data=AdminTicketOutputSerializer(ticket).data,
            message="Hủy vé thành công.",
        )


class AdminTicketRestoreView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]

    @swagger_auto_schema(
        operation_summary="Restore Admin Ticket",
        request_body=AdminTicketCancelInputSerializer,
        responses={200: AdminTicketEnvelopeResponseSerializer(), **ADMIN_TICKET_ERROR_RESPONSES},
        tags=["Admin Ticket Management"],
    )
    def post(self, request, pk):
        serializer = AdminTicketCancelInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ticket = AdminTicketService.restore_ticket(
            actor=request.user,
            ticket_id=pk,
            reason=serializer.validated_data.get("reason", ""),
        )
        return success_response(
            data=AdminTicketOutputSerializer(ticket).data,
            message="Khôi phục vé thành công.",
        )


class AdminTicketCheckinScanView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]

    @swagger_auto_schema(
        operation_summary="Scan Admin Ticket Check-in",
        request_body=AdminTicketScanInputSerializer,
        responses={200: AdminTicketScanEnvelopeResponseSerializer(), **ADMIN_TICKET_ERROR_RESPONSES},
        tags=["Admin Ticket Management"],
    )
    def post(self, request):
        serializer = AdminTicketScanInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = AdminTicketService.process_admin_checkin(
            actor=request.user,
            **serializer.validated_data,
        )
        return success_response(
            data=AdminTicketScanResultSerializer(result).data,
            message="Quét check-in thành công.",
        )


class AdminCheckinLogListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]
    serializer_class = AdminCheckinLogOutputSerializer
    pagination_class = AdminStandardPagination
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = [
        "ticket__ticket_code",
        "ticket__registration__user__username",
        "ticket__registration__user__email",
        "event__title",
    ]
    ordering_fields = ["checked_in_at", "created_at", "method"]
    ordering = ["-checked_in_at", "-created_at"]

    def get_queryset(self):
        params = self.request.query_params
        return AdminTicketService.list_checkins(
            event_id=params.get("event_id"),
            ticket_id=params.get("ticket_id"),
            user_id=params.get("user_id"),
            date_from=params.get("date_from"),
            date_to=params.get("date_to"),
        )

    @swagger_auto_schema(
        operation_summary="List Admin Check-in Logs",
        manual_parameters=[
            openapi.Parameter("event_id", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False),
            openapi.Parameter("ticket_id", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False),
            openapi.Parameter("user_id", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False),
            openapi.Parameter("search", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False),
            openapi.Parameter("date_from", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False),
            openapi.Parameter("date_to", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False),
            openapi.Parameter("ordering", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False),
        ],
        responses={200: AdminCheckinLogListEnvelopeResponseSerializer(), **ADMIN_TICKET_ERROR_RESPONSES},
        tags=["Admin Ticket Management"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class AdminTicketExportView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]

    @swagger_auto_schema(
        operation_summary="Download Tickets Export",
        manual_parameters=[
            openapi.Parameter("export_format", openapi.IN_QUERY, type=openapi.TYPE_STRING, enum=["csv", "xlsx"], required=False),
            openapi.Parameter("format", openapi.IN_QUERY, type=openapi.TYPE_STRING, enum=["csv", "xlsx"], required=False),
            openapi.Parameter("status", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False),
            openapi.Parameter("event_id", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False),
            openapi.Parameter("user_id", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False),
            openapi.Parameter("search", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False),
            openapi.Parameter("date_from", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False),
            openapi.Parameter("date_to", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False),
        ],
        responses={200: AdminCsvExportResponseSerializer(), **ADMIN_TICKET_ERROR_RESPONSES},
        tags=["Admin Ticket Management"],
    )
    def get(self, request):
        params = request.query_params
        filters = {
            key: value
            for key, value in {
                "status": params.get("status"),
                "event_id": params.get("event_id"),
                "user_id": params.get("user_id"),
                "search": params.get("search"),
                "date_from": params.get("date_from"),
                "date_to": params.get("date_to"),
            }.items()
            if value
        }
        return AdminTicketService.build_export_response(
            actor=request.user,
            filters=filters,
            export_format=params.get("export_format") or params.get("format"),
        )
