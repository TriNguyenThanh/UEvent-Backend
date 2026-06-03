import uuid

from django.conf import settings
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView

from apps.events.serializers import (
    OrganizerEventDetailOutputSerializer,
    OrganizerEventInputSerializer,
    OrganizerEventListOutputSerializer,
    OrganizerEventListWithRoleOutputSerializer,
    OrganizerEventPresignedUrlInputSerializer,
    OrganizerEventPresignedUrlOutputSerializer,
    PublicEventCategorySerializer,
    PublicEventDetailOutputSerializer,
    PublicEventShareLinkOutputSerializer,
    PublicEventSearchQuerySerializer,
    PublicEventSearchOutputSerializer,
)
from apps.events.models import EventCategory
from apps.events.services import OrganizerEventService, PublicEventService, UserEventService
from apps.utils.s3 import S3Client
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


class PublicEventCategoryListView(generics.ListAPIView):
    """
    GET /api/v1/event-categories/ - List active event categories
    """
    permission_classes = [AllowAny]
    serializer_class = PublicEventCategorySerializer
    pagination_class = None

    def get_queryset(self):
        return EventCategory.objects.filter(is_active=True).order_by("name")

    @swagger_auto_schema(
        operation_summary="List Event Categories",
        operation_description="Get active event categories for public event browsing.",
        responses={200: PublicEventCategorySerializer(many=True)},
        tags=["Events"],
    )
    def get(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return success_response(data=serializer.data)


class PublicEventSearchView(generics.ListAPIView):
    """
    GET /api/v1/events/search/ - Search public events for every role
    """
    permission_classes = [AllowAny]
    pagination_class = EnvelopePageNumberPagination
    serializer_class = PublicEventSearchOutputSerializer

    def get_queryset(self):
        query_serializer = PublicEventSearchQuerySerializer(data=self.request.query_params)
        query_serializer.is_valid(raise_exception=True)
        return PublicEventService.search_public_events(
            search=query_serializer.get_search_value(),
            category=query_serializer.get_category_value(),
            status=query_serializer.validated_data.get("status"),
            ordering=query_serializer.validated_data.get("ordering"),
        )

    @swagger_auto_schema(
        operation_summary="Search Public Events",
        operation_description="Search public approved or active events. This endpoint is available to every role.",
        manual_parameters=[
            openapi.Parameter("search", openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter(
                "category",
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                description="Category slug or name.",
            ),
            openapi.Parameter(
                "status",
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                enum=["approved", "active"],
            ),
            openapi.Parameter("ordering", openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter("page", openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
            openapi.Parameter("page_size", openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
        ],
        responses={200: PublicEventSearchOutputSerializer(many=True)},
        tags=["Events"],
    )
    def get(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return success_response(data=serializer.data)


class PublicEventDetailView(APIView):
    """
    GET /api/v1/events/<uuid>/ - Get public event detail for users
    """
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="Get Public Event Detail",
        operation_description="Get a public approved or active event detail for users.",
        responses={200: PublicEventDetailOutputSerializer(), **ORGANIZER_EVENT_ERROR_RESPONSES},
        tags=["Events"],
    )
    def get(self, request, pk):
        event = PublicEventService.get_public_event(pk)
        serializer = PublicEventDetailOutputSerializer(event, context={"request": request})
        return success_response(data=serializer.data)


class PublicEventDetailBySlugView(APIView):
    """
    GET /api/v1/events/slug/<slug>/ - Get public event detail for landing pages
    """
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="Get Public Event Detail By Slug",
        operation_description="Get a public approved or active event detail by slug for public landing pages.",
        responses={200: PublicEventDetailOutputSerializer(), **ORGANIZER_EVENT_ERROR_RESPONSES},
        tags=["Events"],
    )
    def get(self, request, slug):
        event = PublicEventService.get_public_event_by_slug(slug)
        serializer = PublicEventDetailOutputSerializer(event, context={"request": request})
        return success_response(data=serializer.data)


class PublicEventShareLinkView(APIView):
    """
    GET /api/v1/events/<uuid>/share-link/ - Get public event share link
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Get Public Event Share Link",
        operation_description="Get the canonical public share link for a public approved or active event.",
        responses={200: PublicEventShareLinkOutputSerializer(), **ORGANIZER_EVENT_ERROR_RESPONSES},
        tags=["Events"],
    )
    def get(self, request, pk):
        event = PublicEventService.get_shareable_public_event(pk)
        serializer = PublicEventShareLinkOutputSerializer(
            {
                "event_id": event.id,
                "slug": event.slug,
                "share_url": PublicEventService.build_share_url(event),
                "visibility": event.visibility,
            }
        )
        return success_response(
            data=serializer.data,
            message="Lấy liên kết chia sẻ thành công.",
        )


class MyEventHighlightsView(APIView):
    """
    GET /api/v1/events/me/highlights/ - Get two relevant events for current user
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Get My Event Highlights",
        operation_description=(
            "Lấy tối đa 2 sự kiện của user hiện tại. Ưu tiên sự kiện user đã đăng ký "
            "bất kể trạng thái đăng ký; nếu thiếu thì bổ sung sự kiện user đã tạo."
        ),
        responses={200: OrganizerEventListOutputSerializer(many=True), **ORGANIZER_EVENT_ERROR_RESPONSES},
        tags=["Events"],
    )
    def get(self, request, *args, **kwargs):
        events = UserEventService.highlight_events_for_user(request.user, limit=2)
        serializer = OrganizerEventListOutputSerializer(events, many=True)
        return success_response(data=serializer.data)


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
        return OrganizerEventListWithRoleOutputSerializer

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
        responses={200: OrganizerEventListWithRoleOutputSerializer(many=True), **ORGANIZER_EVENT_ERROR_RESPONSES},
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


class OrganizerEventPresignedUrlView(APIView):
    """
    POST /api/v1/organizer/events/presigned-url/ - Create S3 presigned URL for event assets
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Create Organizer Event Upload URL",
        operation_description="Create a presigned S3 URL for uploading organizer event cover images.",
        request_body=OrganizerEventPresignedUrlInputSerializer,
        responses={200: OrganizerEventPresignedUrlOutputSerializer(), **ORGANIZER_EVENT_ERROR_RESPONSES},
        tags=["Organizer Events"],
    )
    def post(self, request, *args, **kwargs):
        serializer = OrganizerEventPresignedUrlInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        file_name = serializer.validated_data["file_name"]
        content_type = serializer.validated_data["content_type"]
        object_key = f"events/{request.user.id}/covers/{uuid.uuid4().hex}-{file_name}"

        s3_client = S3Client()
        expires_in = settings.AWS_S3_PRESIGNED_URL_EXPIRES
        presigned_url = s3_client.generate_presigned_url(
            object_key,
            method="put_object",
            expires_in=expires_in,
            params={"ContentType": content_type},
        )

        output_serializer = OrganizerEventPresignedUrlOutputSerializer(
            {
                "object_key": object_key,
                "presigned_upload_url": presigned_url,
                "presigned_url": presigned_url,
                "method": "PUT",
                "expires_in": expires_in,
            }
        )
        return success_response(
            data=output_serializer.data,
            message="Tạo presigned URL thành công.",
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
