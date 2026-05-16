from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.events.serializers import (
    OrganizerEventDetailOutputSerializer,
    OrganizerEventInputSerializer,
    OrganizerEventListOutputSerializer,
)
from apps.events.services import OrganizerEventService
from common.exceptions import ForbiddenError, NotFoundError
from common.pagination import EnvelopePageNumberPagination
from common.responses import created_response, deleted_response, success_response
from common.serializers import ApiErrorResponseSerializer


ORGANIZER_EVENT_ERROR_RESPONSES = {
    400: ApiErrorResponseSerializer(),
    401: ApiErrorResponseSerializer(),
    403: ApiErrorResponseSerializer(),
    404: ApiErrorResponseSerializer(),
}


class OrganizerEventListCreateView(generics.ListCreateAPIView):
    """
    GET /api/v1/organizer/events/ - List organizer's events
    POST /api/v1/organizer/events/ - Create new event
    """
    permission_classes = [IsAuthenticated]
    pagination_class = EnvelopePageNumberPagination
    serializer_class = OrganizerEventListOutputSerializer

    def get_queryset(self):
        return OrganizerEventService.list_events(
            actor=self.request.user,
            status=self.request.query_params.get("status"),
            category_id=self.request.query_params.get("category"),
            visibility=self.request.query_params.get("visibility"),
            search=self.request.query_params.get("search"),
            ordering=self.request.query_params.get("ordering"),
        )

    def get_serializer_class(self):
        if self.request.method == "POST":
            return OrganizerEventInputSerializer
        return OrganizerEventListOutputSerializer

    @swagger_auto_schema(
        operation_summary="List Organizer Events",
        operation_description="Get list of events for the authenticated organizer.",
        manual_parameters=[
            openapi.Parameter("status", openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter("category", openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter("visibility", openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter("search", openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter("ordering", openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter("page", openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
            openapi.Parameter("page_size", openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
        ],
        responses={200: OrganizerEventListOutputSerializer(many=True), **ORGANIZER_EVENT_ERROR_RESPONSES},
        tags=["Organizer Events"],
    )
    def get(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return success_response(data=serializer.data)

    @swagger_auto_schema(
        operation_summary="Create Organizer Event",
        operation_description="Create a new event as organizer.",
        request_body=OrganizerEventInputSerializer,
        responses={201: OrganizerEventDetailOutputSerializer(), **ORGANIZER_EVENT_ERROR_RESPONSES},
        tags=["Organizer Events"],
    )
    def post(self, request, *args, **kwargs):
        serializer = OrganizerEventInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        event = OrganizerEventService.create_event(
            actor=request.user,
            data=serializer.to_service_data(),
        )

        response_serializer = OrganizerEventDetailOutputSerializer(event)
        return created_response(
            data=response_serializer.data,
            message="Tạo sự kiện thành công.",
        )


class OrganizerEventDetailUpdateDeleteView(APIView):
    """
    GET /api/v1/organizer/events/<uuid>/ - Get event detail
    PATCH /api/v1/organizer/events/<uuid>/ - Update event
    DELETE /api/v1/organizer/events/<uuid>/ - Soft delete event
    """
    permission_classes = [IsAuthenticated]

    def get_event(self, pk):
        try:
            return OrganizerEventService.get_event(actor=self.request.user, event_id=pk)
        except (NotFoundError, ForbiddenError) as e:
            raise e

    @swagger_auto_schema(
        operation_summary="Get Organizer Event Detail",
        operation_description="Get single event detail for organizer.",
        responses={200: OrganizerEventDetailOutputSerializer(), **ORGANIZER_EVENT_ERROR_RESPONSES},
        tags=["Organizer Events"],
    )
    def get(self, request, pk):
        event = self.get_event(pk)
        serializer = OrganizerEventDetailOutputSerializer(event)
        return success_response(data=serializer.data)

    @swagger_auto_schema(
        operation_summary="Update Organizer Event",
        operation_description="Update event fields. Only allowed fields are writable.",
        request_body=OrganizerEventInputSerializer,
        responses={200: OrganizerEventDetailOutputSerializer(), **ORGANIZER_EVENT_ERROR_RESPONSES},
        tags=["Organizer Events"],
    )
    def patch(self, request, pk):
        event = self.get_event(pk)
        serializer = OrganizerEventInputSerializer(instance=event, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        updated_event = OrganizerEventService.update_event(
            actor=request.user,
            event_id=pk,
            data=serializer.to_service_data(),
        )

        response_serializer = OrganizerEventDetailOutputSerializer(updated_event)
        return success_response(
            data=response_serializer.data,
            message="Cập nhật sự kiện thành công.",
        )

    @swagger_auto_schema(
        operation_summary="Delete Organizer Event",
        operation_description="Soft delete event.",
        responses={200: ApiErrorResponseSerializer(), **ORGANIZER_EVENT_ERROR_RESPONSES},
        tags=["Organizer Events"],
    )
    def delete(self, request, pk):
        self.get_event(pk)
        OrganizerEventService.delete_event(actor=request.user, event_id=pk)
        return deleted_response(message="Xóa sự kiện thành công.")
