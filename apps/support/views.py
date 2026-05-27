from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status
from rest_framework.views import APIView

from apps.support.models import LegalDocument, SupportArticle, SupportTicket
from apps.support.serializers import (
    LegalDocumentSerializer,
    SupportArticleDetailSerializer,
    SupportCategoryHelpCenterSerializer,
    SupportTicketCreateSerializer,
    SupportTicketMessageCreateSerializer,
    SupportTicketSerializer,
)
from apps.support.services import (
    HelpCenterService,
    LegalDocumentService,
    UserSupportTicketService,
)
from common.response_codes import ResponseCode
from common.responses import created_response, error_response, success_response


class HelpCenterView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        locale = request.query_params.get("locale") or "vi"
        category = request.query_params.get("category") or None
        search = request.query_params.get("search") or None

        categories = HelpCenterService.list_categories(
            locale=locale,
            category=category,
            search=search,
        )
        return success_response(
            data=SupportCategoryHelpCenterSerializer(categories, many=True).data,
            message="Lấy nội dung Trung tâm hỗ trợ thành công.",
            meta={"locale": locale},
        )


class HelpCenterArticleDetailView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, slug):
        locale = request.query_params.get("locale") or "vi"
        try:
            article = HelpCenterService.get_published_article(
                slug=slug,
                locale=locale,
            )
        except SupportArticle.DoesNotExist:
            return error_response(
                code=ResponseCode.NOT_FOUND,
                message="Không tìm thấy bài viết hỗ trợ.",
                errors={"slug": slug},
                status_code=status.HTTP_404_NOT_FOUND,
            )
        return success_response(
            data=SupportArticleDetailSerializer(article).data,
            message="Lấy bài viết hỗ trợ thành công.",
            meta={"locale": locale},
        )


class LegalDocumentDetailView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, document_type):
        locale = request.query_params.get("locale") or "vi"
        try:
            document = LegalDocumentService.get_latest_published(
                document_type=document_type,
                locale=locale,
            )
        except LegalDocument.DoesNotExist:
            return error_response(
                code=ResponseCode.NOT_FOUND,
                message="Không tìm thấy tài liệu pháp lý.",
                errors={"document_type": document_type, "locale": locale},
                status_code=status.HTTP_404_NOT_FOUND,
            )

        return success_response(
            data=LegalDocumentSerializer(document).data,
            message="Lấy tài liệu pháp lý thành công.",
            meta={"locale": locale, "document_type": document_type},
        )


class SupportTicketListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        tickets = UserSupportTicketService.list_tickets(user=request.user)
        return success_response(
            data=SupportTicketSerializer(tickets, many=True).data,
            message="Lấy danh sách yêu cầu hỗ trợ thành công.",
        )

    def post(self, request):
        serializer = SupportTicketCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ticket = UserSupportTicketService.create_ticket(
            user=request.user,
            data=serializer.to_service_data(),
        )
        return created_response(
            data=SupportTicketSerializer(ticket).data,
            message="Đã gửi yêu cầu hỗ trợ.",
        )


class SupportTicketDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        ticket = _get_user_ticket(request.user, pk)
        if ticket is None:
            return _ticket_not_found()
        return success_response(
            data=SupportTicketSerializer(ticket).data,
            message="Lấy chi tiết yêu cầu hỗ trợ thành công.",
        )


class SupportTicketMessageCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        ticket = _get_user_ticket(request.user, pk)
        if ticket is None:
            return _ticket_not_found()

        serializer = SupportTicketMessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ticket = UserSupportTicketService.add_message(
            user=request.user,
            ticket=ticket,
            **serializer.to_service_data(),
        )
        return created_response(
            data=SupportTicketSerializer(ticket).data,
            message="Đã gửi phản hồi hỗ trợ.",
        )


def _get_user_ticket(user, pk):
    try:
        return UserSupportTicketService.get_ticket(user=user, ticket_id=pk)
    except SupportTicket.DoesNotExist:
        return None


def _ticket_not_found():
    return error_response(
        code=ResponseCode.NOT_FOUND,
        message="Không tìm thấy yêu cầu hỗ trợ.",
        errors={"detail": "Không tìm thấy yêu cầu hỗ trợ."},
        status_code=status.HTTP_404_NOT_FOUND,
    )
