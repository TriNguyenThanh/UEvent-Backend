from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from common.responses import created_response, deleted_response, success_response

from ..pagination import AdminStandardPagination
from ..permissions import IsAdminOrSuperUser
from ..serializers.category_serializers import (
    AdminCategoryInputSerializer,
    AdminCategoryOutputSerializer,
    AdminCategoryStatisticsOutputSerializer,
)
from ..serializers.common_serializers import AdminErrorResponseSerializer
from ..serializers.response_serializers import (
    AdminCategoryEnvelopeResponseSerializer,
    AdminCategoryListEnvelopeResponseSerializer,
    AdminCategoryStatisticsEnvelopeResponseSerializer,
)
from ..services.category_services import AdminCategoryService


ADMIN_CATEGORY_ERROR_RESPONSES = {
    400: AdminErrorResponseSerializer(),
    401: AdminErrorResponseSerializer(),
    403: AdminErrorResponseSerializer(),
    404: AdminErrorResponseSerializer(),
}


class AdminCategoryListCreateView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]
    serializer_class = AdminCategoryOutputSerializer
    pagination_class = AdminStandardPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["is_active"]
    search_fields = ["name", "slug", "description"]
    ordering_fields = ["name", "created_at", "event_count"]
    ordering = ["name"]

    def get_queryset(self):
        return AdminCategoryService.list_categories()

    @swagger_auto_schema(
        operation_summary="List Admin Categories",
        responses={200: AdminCategoryListEnvelopeResponseSerializer(), **ADMIN_CATEGORY_ERROR_RESPONSES},
        tags=["Admin Category Management"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Create Admin Category",
        request_body=AdminCategoryInputSerializer,
        responses={201: AdminCategoryEnvelopeResponseSerializer(), **ADMIN_CATEGORY_ERROR_RESPONSES},
        tags=["Admin Category Management"],
    )
    def post(self, request):
        serializer = AdminCategoryInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        category = AdminCategoryService.create_category(
            actor=request.user,
            data=serializer.to_service_data(),
        )
        return created_response(
            data=AdminCategoryOutputSerializer(category).data,
            message="Tạo danh mục thành công.",
        )


class AdminCategoryStatisticsView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]

    @swagger_auto_schema(
        operation_summary="Category Statistics",
        responses={200: AdminCategoryStatisticsEnvelopeResponseSerializer(), **ADMIN_CATEGORY_ERROR_RESPONSES},
        tags=["Admin Category Management"],
    )
    def get(self, request):
        data = AdminCategoryService.get_category_statistics()
        return success_response(
            data=AdminCategoryStatisticsOutputSerializer(data).data,
            message="Lấy thống kê danh mục thành công.",
        )


class AdminCategoryDetailUpdateDeleteView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]

    @swagger_auto_schema(
        operation_summary="Get Admin Category",
        responses={200: AdminCategoryEnvelopeResponseSerializer(), **ADMIN_CATEGORY_ERROR_RESPONSES},
        tags=["Admin Category Management"],
    )
    def get(self, request, pk):
        category = AdminCategoryService.get_category(pk)
        return success_response(
            data=AdminCategoryOutputSerializer(category).data,
            message="Lấy thông tin danh mục thành công.",
        )

    @swagger_auto_schema(
        operation_summary="Update Admin Category",
        request_body=AdminCategoryInputSerializer,
        responses={200: AdminCategoryEnvelopeResponseSerializer(), **ADMIN_CATEGORY_ERROR_RESPONSES},
        tags=["Admin Category Management"],
    )
    def patch(self, request, pk):
        category = AdminCategoryService.get_category(pk)
        serializer = AdminCategoryInputSerializer(instance=category, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        category = AdminCategoryService.update_category(
            actor=request.user,
            category_id=pk,
            data=serializer.to_service_data(),
        )
        return success_response(
            data=AdminCategoryOutputSerializer(category).data,
            message="Cập nhật danh mục thành công.",
        )

    @swagger_auto_schema(
        operation_summary="Delete Admin Category",
        responses={200: AdminCategoryEnvelopeResponseSerializer(), **ADMIN_CATEGORY_ERROR_RESPONSES},
        tags=["Admin Category Management"],
    )
    def delete(self, request, pk):
        AdminCategoryService.delete_category(
            actor=request.user,
            category_id=pk,
            reason=request.data.get("reason", ""),
        )
        return deleted_response(message="Xóa hoặc vô hiệu hóa danh mục thành công.")
