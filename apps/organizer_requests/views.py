from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.system_admin.pagination import AdminStandardPagination
from apps.system_admin.permissions import IsAdminOrSuperUser
from common.responses import created_response, success_response

from apps.organizer_requests.models import OrganizerRequest
from apps.organizer_requests.serializers import (
    AdminOrganizerRequestOutputSerializer,
    AdminOrganizerRequestReviewSerializer,
    OrganizerRequestCreateSerializer,
    OrganizerRequestOutputSerializer,
    OrganizerRequestProofUploadInputSerializer,
    OrganizerRequestProofUploadOutputSerializer,
)
from apps.organizer_requests.services import OrganizerRequestService


ORGANIZER_REQUEST_ERROR_RESPONSES = {
    400: openapi.Response("Dữ liệu không hợp lệ."),
    401: openapi.Response("Chưa đăng nhập."),
    403: openapi.Response("Không có quyền truy cập."),
    404: openapi.Response("Không tìm thấy yêu cầu."),
}


class OrganizerRequestProofUploadUrlView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Create Organizer Request Proof Upload URL",
        request_body=OrganizerRequestProofUploadInputSerializer,
        responses={200: OrganizerRequestProofUploadOutputSerializer(), **ORGANIZER_REQUEST_ERROR_RESPONSES},
        tags=["Organizer Requests"],
    )
    def post(self, request):
        serializer = OrganizerRequestProofUploadInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = OrganizerRequestService.create_proof_upload_url(
            actor=request.user,
            file_name=serializer.validated_data["file_name"],
            content_type=serializer.validated_data["content_type"],
        )
        return success_response(
            data=OrganizerRequestProofUploadOutputSerializer(data).data,
            message="Tạo URL upload tài liệu chứng minh thành công.",
        )


class OrganizerRequestListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="List My Organizer Requests",
        responses={200: OrganizerRequestOutputSerializer(many=True), **ORGANIZER_REQUEST_ERROR_RESPONSES},
        tags=["Organizer Requests"],
    )
    def get(self, request):
        organizer_requests = OrganizerRequestService.list_my_requests(actor=request.user)
        return success_response(
            data=OrganizerRequestOutputSerializer(organizer_requests, many=True).data,
            message="Lấy danh sách yêu cầu tổ chức sự kiện thành công.",
        )

    @swagger_auto_schema(
        operation_summary="Create Organizer Request",
        request_body=OrganizerRequestCreateSerializer,
        responses={201: OrganizerRequestOutputSerializer(), **ORGANIZER_REQUEST_ERROR_RESPONSES},
        tags=["Organizer Requests"],
    )
    def post(self, request):
        serializer = OrganizerRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        organizer_request = OrganizerRequestService.create_request(
            actor=request.user,
            data=serializer.validated_data,
        )
        return created_response(
            data=OrganizerRequestOutputSerializer(organizer_request).data,
            message="Gửi yêu cầu trở thành người tổ chức sự kiện thành công.",
        )


class MyOrganizerRequestView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Get My Organizer Request",
        responses={200: OrganizerRequestOutputSerializer(), **ORGANIZER_REQUEST_ERROR_RESPONSES},
        tags=["Organizer Requests"],
    )
    def get(self, request):
        organizer_request = OrganizerRequestService.get_current_request(actor=request.user)
        data = OrganizerRequestOutputSerializer(organizer_request).data if organizer_request else None
        return success_response(
            data=data,
            message="Lấy trạng thái yêu cầu tổ chức sự kiện thành công.",
        )


class OrganizerRequestCancelView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Cancel My Organizer Request",
        responses={200: OrganizerRequestOutputSerializer(), **ORGANIZER_REQUEST_ERROR_RESPONSES},
        tags=["Organizer Requests"],
    )
    def delete(self, request, pk):
        organizer_request = OrganizerRequestService.cancel_request(
            actor=request.user,
            request_id=pk,
        )
        return success_response(
            data=OrganizerRequestOutputSerializer(organizer_request).data,
            message="Hủy yêu cầu tổ chức sự kiện thành công.",
        )


class AdminOrganizerRequestListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]
    serializer_class = AdminOrganizerRequestOutputSerializer
    pagination_class = AdminStandardPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["status"]
    search_fields = ["user__username", "user__email", "user__full_name", "proof_file_name"]
    ordering_fields = ["created_at", "reviewed_at", "status"]

    def get_queryset(self):
        return OrganizerRequestService.list_requests()

    @swagger_auto_schema(
        operation_summary="List Organizer Requests",
        responses={200: AdminOrganizerRequestOutputSerializer(many=True), **ORGANIZER_REQUEST_ERROR_RESPONSES},
        tags=["Admin Organizer Requests"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class AdminOrganizerRequestStatisticsView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]

    @swagger_auto_schema(
        operation_summary="Get Organizer Request Statistics",
        tags=["Admin Organizer Requests"],
    )
    def get(self, request):
        return success_response(
            data=OrganizerRequestService.get_statistics(),
            message="Lấy thống kê yêu cầu tổ chức sự kiện thành công.",
        )


class AdminOrganizerRequestDetailView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]

    @swagger_auto_schema(
        operation_summary="Get Organizer Request Detail",
        responses={200: AdminOrganizerRequestOutputSerializer(), **ORGANIZER_REQUEST_ERROR_RESPONSES},
        tags=["Admin Organizer Requests"],
    )
    def get(self, request, pk):
        organizer_request = OrganizerRequestService.get_request(pk)
        return success_response(
            data=AdminOrganizerRequestOutputSerializer(organizer_request).data,
            message="Lấy chi tiết yêu cầu tổ chức sự kiện thành công.",
        )


class AdminOrganizerRequestApproveView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]

    @swagger_auto_schema(
        operation_summary="Approve Organizer Request",
        request_body=AdminOrganizerRequestReviewSerializer,
        responses={200: AdminOrganizerRequestOutputSerializer(), **ORGANIZER_REQUEST_ERROR_RESPONSES},
        tags=["Admin Organizer Requests"],
    )
    def post(self, request, pk):
        serializer = AdminOrganizerRequestReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        organizer_request = OrganizerRequestService.approve_request(
            actor=request.user,
            request_id=pk,
            note=serializer.validated_data.get("note", ""),
        )
        return success_response(
            data=AdminOrganizerRequestOutputSerializer(organizer_request).data,
            message="Duyệt yêu cầu tổ chức sự kiện thành công.",
        )


class AdminOrganizerRequestRejectView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]

    @swagger_auto_schema(
        operation_summary="Reject Organizer Request",
        request_body=AdminOrganizerRequestReviewSerializer,
        responses={200: AdminOrganizerRequestOutputSerializer(), **ORGANIZER_REQUEST_ERROR_RESPONSES},
        tags=["Admin Organizer Requests"],
    )
    def post(self, request, pk):
        serializer = AdminOrganizerRequestReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        organizer_request = OrganizerRequestService.reject_request(
            actor=request.user,
            request_id=pk,
            note=serializer.validated_data.get("note", ""),
        )
        return success_response(
            data=AdminOrganizerRequestOutputSerializer(organizer_request).data,
            message="Từ chối yêu cầu tổ chức sự kiện thành công.",
        )
