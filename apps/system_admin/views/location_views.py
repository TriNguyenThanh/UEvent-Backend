from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from common.responses import created_response, deleted_response, success_response

from ..pagination import AdminStandardPagination
from ..permissions import IsAdminOrSuperUser
from ..serializers.common_serializers import AdminErrorResponseSerializer
from ..serializers.location_serializers import (
    AdminBuildingInputSerializer,
    AdminBuildingOutputSerializer,
    AdminCampusInputSerializer,
    AdminCampusOutputSerializer,
    AdminLocationStatisticsOutputSerializer,
    AdminRoomInputSerializer,
    AdminRoomOutputSerializer,
)
from ..serializers.response_serializers import (
    AdminBuildingEnvelopeResponseSerializer,
    AdminBuildingListEnvelopeResponseSerializer,
    AdminCampusEnvelopeResponseSerializer,
    AdminCampusListEnvelopeResponseSerializer,
    AdminLocationStatisticsEnvelopeResponseSerializer,
    AdminRoomEnvelopeResponseSerializer,
    AdminRoomListEnvelopeResponseSerializer,
)
from ..services.location_services import AdminLocationService


ADMIN_LOCATION_ERROR_RESPONSES = {
    400: AdminErrorResponseSerializer(),
    401: AdminErrorResponseSerializer(),
    403: AdminErrorResponseSerializer(),
    404: AdminErrorResponseSerializer(),
}


class AdminCampusListCreateView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]
    serializer_class = AdminCampusOutputSerializer
    pagination_class = AdminStandardPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["is_active"]
    search_fields = ["name", "code", "address"]
    ordering_fields = [
        "name",
        "code",
        "created_at",
        "building_count",
        "room_count",
        "event_count",
    ]
    ordering = ["name"]

    def get_queryset(self):
        return AdminLocationService.list_campuses()

    @swagger_auto_schema(
        operation_summary="List Admin Campuses",
        responses={200: AdminCampusListEnvelopeResponseSerializer(), **ADMIN_LOCATION_ERROR_RESPONSES},
        tags=["Admin Location Management"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Create Admin Campus",
        request_body=AdminCampusInputSerializer,
        responses={201: AdminCampusEnvelopeResponseSerializer(), **ADMIN_LOCATION_ERROR_RESPONSES},
        tags=["Admin Location Management"],
    )
    def post(self, request):
        serializer = AdminCampusInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        campus = AdminLocationService.create_campus(
            actor=request.user,
            data=serializer.to_service_data(),
        )
        return created_response(
            data=AdminCampusOutputSerializer(campus).data,
            message="Tạo cơ sở thành công.",
        )


class AdminCampusDetailUpdateDeleteView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]

    @swagger_auto_schema(
        operation_summary="Get Admin Campus",
        responses={200: AdminCampusEnvelopeResponseSerializer(), **ADMIN_LOCATION_ERROR_RESPONSES},
        tags=["Admin Location Management"],
    )
    def get(self, request, pk):
        campus = AdminLocationService.get_campus(pk)
        return success_response(
            data=AdminCampusOutputSerializer(campus).data,
            message="Lấy thông tin cơ sở thành công.",
        )

    @swagger_auto_schema(
        operation_summary="Update Admin Campus",
        request_body=AdminCampusInputSerializer,
        responses={200: AdminCampusEnvelopeResponseSerializer(), **ADMIN_LOCATION_ERROR_RESPONSES},
        tags=["Admin Location Management"],
    )
    def patch(self, request, pk):
        campus = AdminLocationService.get_campus(pk)
        serializer = AdminCampusInputSerializer(instance=campus, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        campus = AdminLocationService.update_campus(
            actor=request.user,
            campus_id=pk,
            data=serializer.to_service_data(),
        )
        return success_response(
            data=AdminCampusOutputSerializer(campus).data,
            message="Cập nhật cơ sở thành công.",
        )

    @swagger_auto_schema(
        operation_summary="Delete Admin Campus",
        responses={200: AdminCampusEnvelopeResponseSerializer(), **ADMIN_LOCATION_ERROR_RESPONSES},
        tags=["Admin Location Management"],
    )
    def delete(self, request, pk):
        AdminLocationService.delete_campus(
            actor=request.user,
            campus_id=pk,
            reason=request.data.get("reason", ""),
        )
        return deleted_response(message="Xóa hoặc vô hiệu hóa cơ sở thành công.")


class AdminBuildingListCreateView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]
    serializer_class = AdminBuildingOutputSerializer
    pagination_class = AdminStandardPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["is_active"]
    search_fields = ["name", "code", "campus__name", "campus__code"]
    ordering_fields = [
        "campus__name",
        "name",
        "code",
        "created_at",
        "room_count",
        "event_count",
    ]
    ordering = ["campus__name", "name"]

    def get_queryset(self):
        queryset = AdminLocationService.list_buildings()
        campus_id = self.request.query_params.get("campus")
        if campus_id:
            queryset = queryset.filter(campus_id=campus_id)
        return queryset

    @swagger_auto_schema(
        operation_summary="List Admin Buildings",
        responses={200: AdminBuildingListEnvelopeResponseSerializer(), **ADMIN_LOCATION_ERROR_RESPONSES},
        tags=["Admin Location Management"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Create Admin Building",
        request_body=AdminBuildingInputSerializer,
        responses={201: AdminBuildingEnvelopeResponseSerializer(), **ADMIN_LOCATION_ERROR_RESPONSES},
        tags=["Admin Location Management"],
    )
    def post(self, request):
        serializer = AdminBuildingInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        building = AdminLocationService.create_building(
            actor=request.user,
            data=serializer.to_service_data(),
        )
        return created_response(
            data=AdminBuildingOutputSerializer(building).data,
            message="Tạo tòa nhà thành công.",
        )


class AdminBuildingDetailUpdateDeleteView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]

    @swagger_auto_schema(
        operation_summary="Get Admin Building",
        responses={200: AdminBuildingEnvelopeResponseSerializer(), **ADMIN_LOCATION_ERROR_RESPONSES},
        tags=["Admin Location Management"],
    )
    def get(self, request, pk):
        building = AdminLocationService.get_building(pk)
        return success_response(
            data=AdminBuildingOutputSerializer(building).data,
            message="Lấy thông tin tòa nhà thành công.",
        )

    @swagger_auto_schema(
        operation_summary="Update Admin Building",
        request_body=AdminBuildingInputSerializer,
        responses={200: AdminBuildingEnvelopeResponseSerializer(), **ADMIN_LOCATION_ERROR_RESPONSES},
        tags=["Admin Location Management"],
    )
    def patch(self, request, pk):
        building = AdminLocationService.get_building(pk)
        serializer = AdminBuildingInputSerializer(instance=building, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        building = AdminLocationService.update_building(
            actor=request.user,
            building_id=pk,
            data=serializer.to_service_data(),
        )
        return success_response(
            data=AdminBuildingOutputSerializer(building).data,
            message="Cập nhật tòa nhà thành công.",
        )

    @swagger_auto_schema(
        operation_summary="Delete Admin Building",
        responses={200: AdminBuildingEnvelopeResponseSerializer(), **ADMIN_LOCATION_ERROR_RESPONSES},
        tags=["Admin Location Management"],
    )
    def delete(self, request, pk):
        AdminLocationService.delete_building(
            actor=request.user,
            building_id=pk,
            reason=request.data.get("reason", ""),
        )
        return deleted_response(message="Xóa hoặc vô hiệu hóa tòa nhà thành công.")


class AdminRoomListCreateView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]
    serializer_class = AdminRoomOutputSerializer
    pagination_class = AdminStandardPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["is_active"]
    search_fields = [
        "name",
        "code",
        "building__name",
        "building__code",
        "building__campus__name",
        "building__campus__code",
    ]
    ordering_fields = [
        "building__campus__name",
        "building__name",
        "name",
        "capacity",
        "created_at",
        "event_count",
    ]
    ordering = ["building__campus__name", "building__name", "name"]

    def get_queryset(self):
        queryset = AdminLocationService.list_rooms()
        campus_id = self.request.query_params.get("campus")
        building_id = self.request.query_params.get("building")
        if campus_id:
            queryset = queryset.filter(building__campus_id=campus_id)
        if building_id:
            queryset = queryset.filter(building_id=building_id)
        return queryset

    @swagger_auto_schema(
        operation_summary="List Admin Rooms",
        responses={200: AdminRoomListEnvelopeResponseSerializer(), **ADMIN_LOCATION_ERROR_RESPONSES},
        tags=["Admin Location Management"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Create Admin Room",
        request_body=AdminRoomInputSerializer,
        responses={201: AdminRoomEnvelopeResponseSerializer(), **ADMIN_LOCATION_ERROR_RESPONSES},
        tags=["Admin Location Management"],
    )
    def post(self, request):
        serializer = AdminRoomInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        room = AdminLocationService.create_room(
            actor=request.user,
            data=serializer.to_service_data(),
        )
        return created_response(
            data=AdminRoomOutputSerializer(room).data,
            message="Tạo phòng thành công.",
        )


class AdminRoomDetailUpdateDeleteView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]

    @swagger_auto_schema(
        operation_summary="Get Admin Room",
        responses={200: AdminRoomEnvelopeResponseSerializer(), **ADMIN_LOCATION_ERROR_RESPONSES},
        tags=["Admin Location Management"],
    )
    def get(self, request, pk):
        room = AdminLocationService.get_room(pk)
        return success_response(
            data=AdminRoomOutputSerializer(room).data,
            message="Lấy thông tin phòng thành công.",
        )

    @swagger_auto_schema(
        operation_summary="Update Admin Room",
        request_body=AdminRoomInputSerializer,
        responses={200: AdminRoomEnvelopeResponseSerializer(), **ADMIN_LOCATION_ERROR_RESPONSES},
        tags=["Admin Location Management"],
    )
    def patch(self, request, pk):
        room = AdminLocationService.get_room(pk)
        serializer = AdminRoomInputSerializer(instance=room, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        room = AdminLocationService.update_room(
            actor=request.user,
            room_id=pk,
            data=serializer.to_service_data(),
        )
        return success_response(
            data=AdminRoomOutputSerializer(room).data,
            message="Cập nhật phòng thành công.",
        )

    @swagger_auto_schema(
        operation_summary="Delete Admin Room",
        responses={200: AdminRoomEnvelopeResponseSerializer(), **ADMIN_LOCATION_ERROR_RESPONSES},
        tags=["Admin Location Management"],
    )
    def delete(self, request, pk):
        AdminLocationService.delete_room(
            actor=request.user,
            room_id=pk,
            reason=request.data.get("reason", ""),
        )
        return deleted_response(message="Xóa hoặc vô hiệu hóa phòng thành công.")


class AdminLocationStatisticsView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]

    @swagger_auto_schema(
        operation_summary="Location Statistics",
        responses={200: AdminLocationStatisticsEnvelopeResponseSerializer(), **ADMIN_LOCATION_ERROR_RESPONSES},
        tags=["Admin Location Management"],
    )
    def get(self, request):
        data = AdminLocationService.get_statistics()
        return success_response(
            data=AdminLocationStatisticsOutputSerializer(data).data,
            message="Lấy thống kê địa điểm thành công.",
        )
