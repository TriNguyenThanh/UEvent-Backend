from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from django.db import IntegrityError
from rest_framework import generics
from rest_framework import status
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.support.models import LegalDocument, SupportArticle, SupportCategory
from common.response_codes import ResponseCode
from common.responses import (
    created_response,
    deleted_response,
    error_response,
    success_response,
)

from ..pagination import AdminStandardPagination
from ..permissions import IsAdminOrSuperUser
from ..serializers.common_serializers import AdminErrorResponseSerializer
from ..serializers.response_serializers import (
    AdminSupportTicketEnvelopeResponseSerializer,
    AdminSupportTicketListEnvelopeResponseSerializer,
    AdminSupportTicketStatisticsEnvelopeResponseSerializer,
)
from ..serializers.support_serializers import (
    AdminLegalDocumentSerializer,
    AdminSupportEscalateInputSerializer,
    AdminSupportArticleSerializer,
    AdminSupportCategorySerializer,
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
    search_fields = [
        "subject",
        "description",
        "user__username",
        "user__email",
        "user__full_name",
    ]
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
            openapi.Parameter(
                "status", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False
            ),
            openapi.Parameter(
                "priority", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False
            ),
            openapi.Parameter(
                "category", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False
            ),
            openapi.Parameter(
                "search", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False
            ),
            openapi.Parameter(
                "ordering", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False
            ),
        ],
        responses={
            200: AdminSupportTicketListEnvelopeResponseSerializer(),
            **ADMIN_SUPPORT_ERROR_RESPONSES,
        },
        tags=["Admin Support Management"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class AdminSupportTicketStatisticsView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]

    @swagger_auto_schema(
        operation_summary="Support Ticket Statistics",
        responses={
            200: AdminSupportTicketStatisticsEnvelopeResponseSerializer(),
            **ADMIN_SUPPORT_ERROR_RESPONSES,
        },
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
        responses={
            200: AdminSupportTicketEnvelopeResponseSerializer(),
            **ADMIN_SUPPORT_ERROR_RESPONSES,
        },
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
        responses={
            200: AdminSupportTicketEnvelopeResponseSerializer(),
            **ADMIN_SUPPORT_ERROR_RESPONSES,
        },
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
        responses={
            200: AdminSupportTicketEnvelopeResponseSerializer(),
            **ADMIN_SUPPORT_ERROR_RESPONSES,
        },
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
        responses={
            200: AdminSupportTicketEnvelopeResponseSerializer(),
            **ADMIN_SUPPORT_ERROR_RESPONSES,
        },
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
        responses={
            200: AdminSupportTicketEnvelopeResponseSerializer(),
            **ADMIN_SUPPORT_ERROR_RESPONSES,
        },
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


class AdminSupportCategoryListCreateView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]

    def get(self, request):
        categories = AdminSupportService.list_help_center_categories()
        return success_response(
            data=AdminSupportCategorySerializer(categories, many=True).data,
            message="Lấy danh sách danh mục Help Center thành công.",
        )

    def post(self, request):
        serializer = AdminSupportCategorySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            category = serializer.save()
        except IntegrityError:
            return error_response(
                code=ResponseCode.CONFLICT,
                message="Slug danh mục Help Center đã tồn tại.",
                errors={"slug": "Slug đã tồn tại."},
                status_code=status.HTTP_409_CONFLICT,
            )

        AdminSupportService.log_help_center_action(
            action="create_support_category",
            actor=request.user,
            target=category,
        )
        return created_response(
            data=AdminSupportCategorySerializer(category).data,
            message="Tạo danh mục Help Center thành công.",
        )


class AdminSupportCategoryDetailView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]

    def get(self, request, pk):
        category = _get_support_category(pk)
        if category is None:
            return _not_found("Không tìm thấy danh mục Help Center.")
        return success_response(
            data=AdminSupportCategorySerializer(category).data,
            message="Lấy danh mục Help Center thành công.",
        )

    def patch(self, request, pk):
        category = _get_support_category(pk)
        if category is None:
            return _not_found("Không tìm thấy danh mục Help Center.")

        serializer = AdminSupportCategorySerializer(
            category,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        try:
            category = serializer.save()
        except IntegrityError:
            return error_response(
                code=ResponseCode.CONFLICT,
                message="Slug danh mục Help Center đã tồn tại.",
                errors={"slug": "Slug đã tồn tại."},
                status_code=status.HTTP_409_CONFLICT,
            )

        AdminSupportService.log_help_center_action(
            action="update_support_category",
            actor=request.user,
            target=category,
            metadata={"updated_fields": list(serializer.validated_data.keys())},
        )
        return success_response(
            data=AdminSupportCategorySerializer(category).data,
            message="Cập nhật danh mục Help Center thành công.",
        )

    def delete(self, request, pk):
        category = _get_support_category(pk)
        if category is None:
            return _not_found("Không tìm thấy danh mục Help Center.")

        category.delete()
        AdminSupportService.log_help_center_action(
            action="delete_support_category",
            actor=request.user,
            target=category,
        )
        return deleted_response(message="Đã xóa danh mục Help Center.")


class AdminSupportArticleListCreateView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]

    def get(self, request):
        articles = AdminSupportService.list_help_center_articles(
            status=request.query_params.get("status"),
            locale=request.query_params.get("locale"),
            category=request.query_params.get("category"),
        )
        return success_response(
            data=AdminSupportArticleSerializer(articles, many=True).data,
            message="Lấy danh sách bài viết Help Center thành công.",
        )

    def post(self, request):
        serializer = AdminSupportArticleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            article = serializer.save()
        except IntegrityError:
            return error_response(
                code=ResponseCode.CONFLICT,
                message="Slug bài viết Help Center đã tồn tại theo ngôn ngữ.",
                errors={"slug": "Slug và locale đã tồn tại."},
                status_code=status.HTTP_409_CONFLICT,
            )

        AdminSupportService.log_help_center_action(
            action="create_support_article",
            actor=request.user,
            target=article,
        )
        return created_response(
            data=AdminSupportArticleSerializer(article).data,
            message="Tạo bài viết Help Center thành công.",
        )


class AdminSupportArticleDetailView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]

    def get(self, request, pk):
        article = _get_support_article(pk)
        if article is None:
            return _not_found("Không tìm thấy bài viết Help Center.")
        return success_response(
            data=AdminSupportArticleSerializer(article).data,
            message="Lấy bài viết Help Center thành công.",
        )

    def patch(self, request, pk):
        article = _get_support_article(pk)
        if article is None:
            return _not_found("Không tìm thấy bài viết Help Center.")

        serializer = AdminSupportArticleSerializer(
            article,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        try:
            article = serializer.save()
        except IntegrityError:
            return error_response(
                code=ResponseCode.CONFLICT,
                message="Slug bài viết Help Center đã tồn tại theo ngôn ngữ.",
                errors={"slug": "Slug và locale đã tồn tại."},
                status_code=status.HTTP_409_CONFLICT,
            )

        AdminSupportService.log_help_center_action(
            action="update_support_article",
            actor=request.user,
            target=article,
            metadata={"updated_fields": list(serializer.validated_data.keys())},
        )
        return success_response(
            data=AdminSupportArticleSerializer(article).data,
            message="Cập nhật bài viết Help Center thành công.",
        )

    def delete(self, request, pk):
        article = _get_support_article(pk)
        if article is None:
            return _not_found("Không tìm thấy bài viết Help Center.")

        article.delete()
        AdminSupportService.log_help_center_action(
            action="delete_support_article",
            actor=request.user,
            target=article,
        )
        return deleted_response(message="Đã xóa bài viết Help Center.")


class AdminSupportArticlePublishView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]

    def post(self, request, pk):
        article = AdminSupportService.publish_help_center_article(
            actor=request.user,
            article_id=pk,
        )
        return success_response(
            data=AdminSupportArticleSerializer(article).data,
            message="Đã publish bài viết Help Center.",
        )


class AdminSupportArticleArchiveView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]

    def post(self, request, pk):
        article = AdminSupportService.archive_help_center_article(
            actor=request.user,
            article_id=pk,
        )
        return success_response(
            data=AdminSupportArticleSerializer(article).data,
            message="Đã archive bài viết Help Center.",
        )


class AdminLegalDocumentListCreateView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]

    def get(self, request):
        documents = AdminSupportService.list_legal_documents(
            document_type=request.query_params.get("document_type"),
            status=request.query_params.get("status"),
            locale=request.query_params.get("locale"),
        )
        return success_response(
            data=AdminLegalDocumentSerializer(documents, many=True).data,
            message="Lấy danh sách tài liệu pháp lý thành công.",
        )

    def post(self, request):
        serializer = AdminLegalDocumentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            document = serializer.save()
        except IntegrityError:
            return error_response(
                code=ResponseCode.CONFLICT,
                message="Phiên bản tài liệu pháp lý đã tồn tại theo ngôn ngữ.",
                errors={
                    "version": "Document type, version và locale đã tồn tại.",
                },
                status_code=status.HTTP_409_CONFLICT,
            )

        AdminSupportService.log_legal_document_action(
            action="create_legal_document",
            actor=request.user,
            target=document,
        )
        return created_response(
            data=AdminLegalDocumentSerializer(document).data,
            message="Tạo tài liệu pháp lý thành công.",
        )


class AdminLegalDocumentDetailView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]

    def get(self, request, pk):
        document = _get_legal_document(pk)
        if document is None:
            return _not_found("Không tìm thấy tài liệu pháp lý.")
        return success_response(
            data=AdminLegalDocumentSerializer(document).data,
            message="Lấy tài liệu pháp lý thành công.",
        )

    def patch(self, request, pk):
        document = _get_legal_document(pk)
        if document is None:
            return _not_found("Không tìm thấy tài liệu pháp lý.")

        serializer = AdminLegalDocumentSerializer(
            document,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        try:
            document = serializer.save()
        except IntegrityError:
            return error_response(
                code=ResponseCode.CONFLICT,
                message="Phiên bản tài liệu pháp lý đã tồn tại theo ngôn ngữ.",
                errors={
                    "version": "Document type, version và locale đã tồn tại.",
                },
                status_code=status.HTTP_409_CONFLICT,
            )

        AdminSupportService.log_legal_document_action(
            action="update_legal_document",
            actor=request.user,
            target=document,
            metadata={"updated_fields": list(serializer.validated_data.keys())},
        )
        return success_response(
            data=AdminLegalDocumentSerializer(document).data,
            message="Cập nhật tài liệu pháp lý thành công.",
        )

    def delete(self, request, pk):
        document = _get_legal_document(pk)
        if document is None:
            return _not_found("Không tìm thấy tài liệu pháp lý.")

        document.delete()
        AdminSupportService.log_legal_document_action(
            action="delete_legal_document",
            actor=request.user,
            target=document,
        )
        return deleted_response(message="Đã xóa tài liệu pháp lý.")


class AdminLegalDocumentPublishView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]

    def post(self, request, pk):
        document = AdminSupportService.publish_legal_document(
            actor=request.user,
            document_id=pk,
        )
        return success_response(
            data=AdminLegalDocumentSerializer(document).data,
            message="Đã publish tài liệu pháp lý.",
        )


class AdminLegalDocumentArchiveView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]

    def post(self, request, pk):
        document = AdminSupportService.archive_legal_document(
            actor=request.user,
            document_id=pk,
        )
        return success_response(
            data=AdminLegalDocumentSerializer(document).data,
            message="Đã archive tài liệu pháp lý.",
        )


def _get_support_category(pk):
    return SupportCategory.objects.filter(pk=pk).first()


def _get_support_article(pk):
    return SupportArticle.objects.select_related("category").filter(pk=pk).first()


def _get_legal_document(pk):
    return LegalDocument.objects.filter(pk=pk).first()


def _not_found(message):
    return error_response(
        code=ResponseCode.NOT_FOUND,
        message=message,
        errors={"detail": message},
        status_code=status.HTTP_404_NOT_FOUND,
    )
