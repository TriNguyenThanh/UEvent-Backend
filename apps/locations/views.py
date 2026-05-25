from django.db.models import Q
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from apps.locations.models import Room
from apps.locations.serializers import RoomListOutputSerializer
from common.pagination import EnvelopePageNumberPagination
from common.responses import success_response
from common.serializers import ApiErrorResponseSerializer


class RoomListView(generics.ListAPIView):
    """
    GET /api/v1/locations/rooms/ - List active rooms for event creation.
    """
    permission_classes = [IsAuthenticated]
    pagination_class = EnvelopePageNumberPagination
    serializer_class = RoomListOutputSerializer

    def get_queryset(self):
        queryset = Room.objects.filter(
            is_active=True,
            building__is_active=True,
            building__campus__is_active=True,
        ).select_related("building", "building__campus")

        building_id = self.request.query_params.get("building")
        campus_id = self.request.query_params.get("campus")
        search = self.request.query_params.get("search")

        if building_id:
            queryset = queryset.filter(building_id=building_id)
        if campus_id:
            queryset = queryset.filter(building__campus_id=campus_id)
        if search:
            queryset = queryset.filter(Q(name__icontains=search) | Q(code__icontains=search))

        return queryset.order_by("building__campus__name", "building__name", "name")

    @swagger_auto_schema(
        operation_summary="List Rooms",
        operation_description="Get active rooms for organizer event forms.",
        manual_parameters=[
            openapi.Parameter("building", openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter("campus", openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter("search", openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter("page", openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
            openapi.Parameter("page_size", openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
        ],
        responses={
            200: RoomListOutputSerializer(many=True),
            401: ApiErrorResponseSerializer(),
        },
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
