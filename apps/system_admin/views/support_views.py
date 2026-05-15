from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from common.responses import success_response

from ..pagination import AdminStandardPagination
from ..permissions import IsAdminOrSuperUser
from ..serializers.common_serializers import AdminErrorResponseSerializer
from ..serializers.response_serializers import (
    AdminSupportTicketEnvelopeResponseSerializer,
    AdminSupportTicketListEnvelopeResponseSerializer,
    AdminSupportTicketStatisticsEnvelopeResponseSerializer,
)
from ..serializers.support_serializers import (
    AdminSupportEscalateInputSerializer,
    AdminSupportReplyInputSerializer,
    AdminSupportResolveInputSerializer,
    AdminSupportStatisticsOutputSerializer,
    AdminSupportTicketDetailOutputSerializer,
    AdminSupportTicketListOutputSerializer,
    AdminSupportTicketUpdateInputSerializer,
)
from ..services.support_services import AdminSupportService


ADMIN_SUPPORT_ERROR_RESPONSES = {
    400: AdminErrorResponseSerializer(),
    401: AdminErrorResponseSerializer(),
    403: AdminErrorResponseSerializer(),
    404: AdminErrorResponseSerializer(),
}


class AdminSupportTicketListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]
    serializer_class = AdminSupportTicketListOutputSerializer
    pagination_class = AdminStandardPagination
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["subject", "description", "user__username", "user__email", "user__full_name"]
    ordering_fields = ["created_at", "updated_at", "priority", "status"]
    ordering = ["-updated_at", "-created_at"]

    def get_queryset(self):
        params = self.request.query_params
        return AdminSupportService.list_tickets(
            status=params.get("status"),
            priority=params.get("priority"),
            category=params.get("category"),
        )

    @swagger_auto_schema(
        operation_summary="List Admin Support Tickets",
        manual_parameters=[
            openapi.Parameter("status", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False),
            openapi.Parameter("priority", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False),
            openapi.Parameter("category", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False),
            openapi.Parameter("search", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False),
            openapi.Parameter("ordering", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False),
        ],
        responses={200: AdminSupportTicketListEnvelopeResponseSerializer(), **ADMIN_SUPPORT_ERROR_RESPONSES},
        tags=["Admin Support Management"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class AdminSupportTicketStatisticsView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]

    @swagger_auto_schema(
        operation_summary="Support Ticket Statistics",
        responses={200: AdminSupportTicketStatisticsEnvelopeResponseSerializer(), **ADMIN_SUPPORT_ERROR_RESPONSES},
        tags=["Admin Support Management"],
    )
    def get(self, request):
        data = AdminSupportService.get_statistics()
        return success_response(
            data=AdminSupportStatisticsOutputSerializer(data).data,
            message="Lấy thống kê hỗ trợ thành công.",
        )


class AdminSupportTicketDetailUpdateView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]

    @swagger_auto_schema(
        operation_summary="Get Admin Support Ticket",
        responses={200: AdminSupportTicketEnvelopeResponseSerializer(), **ADMIN_SUPPORT_ERROR_RESPONSES},
        tags=["Admin Support Management"],
    )
    def get(self, request, pk):
        ticket = AdminSupportService.get_ticket(pk)
        return success_response(
            data=AdminSupportTicketDetailOutputSerializer(ticket).data,
            message="Lấy chi tiết yêu cầu hỗ trợ thành công.",
        )

    @swagger_auto_schema(
        operation_summary="Update Admin Support Ticket",
        request_body=AdminSupportTicketUpdateInputSerializer,
        responses={200: AdminSupportTicketEnvelopeResponseSerializer(), **ADMIN_SUPPORT_ERROR_RESPONSES},
        tags=["Admin Support Management"],
    )
    def patch(self, request, pk):
        serializer = AdminSupportTicketUpdateInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ticket = AdminSupportService.update_ticket(
            actor=request.user,
            ticket_id=pk,
            data=serializer.to_service_data(),
        )
        return success_response(
            data=AdminSupportTicketDetailOutputSerializer(ticket).data,
            message="Cập nhật yêu cầu hỗ trợ thành công.",
        )


class AdminSupportTicketMessagesView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]

    @swagger_auto_schema(
        operation_summary="Reply To Support Ticket",
        request_body=AdminSupportReplyInputSerializer,
        responses={200: AdminSupportTicketEnvelopeResponseSerializer(), **ADMIN_SUPPORT_ERROR_RESPONSES},
        tags=["Admin Support Management"],
    )
    def post(self, request, pk):
        serializer = AdminSupportReplyInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ticket = AdminSupportService.reply_to_ticket(
            actor=request.user,
            ticket_id=pk,
            **serializer.to_service_data(),
        )
        return success_response(
            data=AdminSupportTicketDetailOutputSerializer(ticket).data,
            message="Gửi phản hồi hỗ trợ thành công.",
        )


class AdminSupportTicketResolveView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]

    @swagger_auto_schema(
        operation_summary="Resolve Support Ticket",
        request_body=AdminSupportResolveInputSerializer,
        responses={200: AdminSupportTicketEnvelopeResponseSerializer(), **ADMIN_SUPPORT_ERROR_RESPONSES},
        tags=["Admin Support Management"],
    )
    def post(self, request, pk):
        serializer = AdminSupportResolveInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ticket = AdminSupportService.resolve_ticket(
            actor=request.user,
            ticket_id=pk,
            **serializer.to_service_data(),
        )
        return success_response(
            data=AdminSupportTicketDetailOutputSerializer(ticket).data,
            message="Đánh dấu yêu cầu hỗ trợ đã xử lý thành công.",
        )


class AdminSupportTicketEscalateView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]

    @swagger_auto_schema(
        operation_summary="Escalate Support Ticket",
        request_body=AdminSupportEscalateInputSerializer,
        responses={200: AdminSupportTicketEnvelopeResponseSerializer(), **ADMIN_SUPPORT_ERROR_RESPONSES},
        tags=["Admin Support Management"],
    )
    def post(self, request, pk):
        serializer = AdminSupportEscalateInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ticket = AdminSupportService.escalate_ticket(
            actor=request.user,
            ticket_id=pk,
            **serializer.to_service_data(),
        )
        return success_response(
            data=AdminSupportTicketDetailOutputSerializer(ticket).data,
            message="Nâng mức ưu tiên yêu cầu hỗ trợ thành công.",
        )
