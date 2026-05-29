from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.support.models import (
    LegalDocument,
    SupportArticle,
    SupportCategory,
    SupportMessage,
    SupportTicket,
)
from common.response_codes import ResponseCode


class HelpCenterPublicApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = SupportCategory.objects.create(
            name="Tài khoản",
            slug="tai-khoan",
            description="Câu hỏi về tài khoản",
            sort_order=1,
        )
        cls.article = SupportArticle.objects.create(
            category=cls.category,
            title="Làm sao đổi email?",
            slug="doi-email",
            summary="Hướng dẫn đổi email tài khoản.",
            body="Mở Chỉnh sửa hồ sơ và chọn Đổi email.",
            locale="vi",
            status=SupportArticle.ArticleStatus.PUBLISHED,
            sort_order=1,
        )
        SupportArticle.objects.create(
            category=cls.category,
            title="Bản nháp không public",
            slug="ban-nhap",
            summary="Không xuất hiện trên mobile.",
            body="Draft content.",
            locale="vi",
            status=SupportArticle.ArticleStatus.DRAFT,
            sort_order=2,
        )

    def setUp(self):
        self.client = APIClient()

    def assert_success_envelope(self, response):
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["code"], ResponseCode.SUCCESS.value)
        self.assertTrue(response.data["success"])
        self.assertIsNone(response.data["errors"])

    def test_help_center_only_returns_published_articles(self):
        response = self.client.get(reverse("support:help-center"), {"locale": "vi"})

        self.assert_success_envelope(response)
        self.assertEqual(len(response.data["data"]), 1)
        articles = response.data["data"][0]["articles"]
        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0]["slug"], self.article.slug)

    def test_help_center_supports_search_and_article_detail(self):
        search_response = self.client.get(
            reverse("support:help-center"),
            {"locale": "vi", "search": "đổi email"},
        )
        self.assert_success_envelope(search_response)
        self.assertEqual(
            search_response.data["data"][0]["articles"][0]["slug"], "doi-email"
        )

        detail_response = self.client.get(
            reverse("support:help-center-article-detail", kwargs={"slug": "doi-email"}),
            {"locale": "vi"},
        )
        self.assert_success_envelope(detail_response)
        self.assertEqual(detail_response.data["data"]["body"], self.article.body)

    def test_help_center_does_not_return_archived_article_detail(self):
        self.article.status = SupportArticle.ArticleStatus.ARCHIVED
        self.article.save(update_fields=["status", "updated_at"])

        response = self.client.get(
            reverse("support:help-center-article-detail", kwargs={"slug": "doi-email"}),
            {"locale": "vi"},
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["code"], ResponseCode.NOT_FOUND.value)


class LegalDocumentPublicApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.document = LegalDocument.objects.create(
            document_type=LegalDocument.DocumentType.PRIVACY_POLICY,
            title="Chính sách quyền riêng tư",
            version="2026-05",
            summary="Cách UEvents xử lý dữ liệu cá nhân.",
            body="Nội dung chính sách quyền riêng tư.",
            locale="vi",
            status=LegalDocument.DocumentStatus.PUBLISHED,
            published_at=timezone.now(),
        )
        LegalDocument.objects.create(
            document_type=LegalDocument.DocumentType.PRIVACY_POLICY,
            title="Bản nháp chính sách",
            version="2026-06",
            summary="Chưa public.",
            body="Draft content.",
            locale="vi",
            status=LegalDocument.DocumentStatus.DRAFT,
        )

    def setUp(self):
        self.client = APIClient()

    def test_legal_document_returns_latest_published_document(self):
        response = self.client.get(
            reverse(
                "support:legal-document-detail",
                kwargs={"document_type": LegalDocument.DocumentType.PRIVACY_POLICY},
            ),
            {"locale": "vi"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["code"], ResponseCode.SUCCESS.value)
        self.assertEqual(response.data["data"]["version"], self.document.version)
        self.assertEqual(response.data["data"]["body"], self.document.body)

    def test_legal_document_returns_404_when_no_published_document_exists(self):
        self.document.status = LegalDocument.DocumentStatus.ARCHIVED
        self.document.save(update_fields=["status", "updated_at"])

        response = self.client.get(
            reverse(
                "support:legal-document-detail",
                kwargs={"document_type": LegalDocument.DocumentType.PRIVACY_POLICY},
            ),
            {"locale": "vi"},
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["code"], ResponseCode.NOT_FOUND.value)


class UserSupportTicketApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.user = user_model.objects.create_user(
            username="student",
            email="student@example.com",
            password="pass123",
        )
        cls.other_user = user_model.objects.create_user(
            username="other",
            email="other@example.com",
            password="pass123",
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_user_can_create_and_list_own_support_ticket(self):
        response = self.client.post(
            reverse("support:ticket-list"),
            {
                "subject": "Cần hỗ trợ đổi email",
                "description": "Tôi không nhận được OTP.",
                "category": SupportTicket.Category.ACCOUNT,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["code"], ResponseCode.CREATED.value)
        self.assertEqual(
            response.data["data"]["status"], SupportTicket.TicketStatus.OPEN
        )
        self.assertEqual(
            response.data["data"]["priority"], SupportTicket.TicketPriority.MEDIUM
        )
        self.assertEqual(
            response.data["data"]["messages"][0]["content"], "Tôi không nhận được OTP."
        )
        self.assertEqual(SupportMessage.objects.count(), 1)

        list_response = self.client.get(reverse("support:ticket-list"))
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(len(list_response.data["data"]), 1)
        self.assertEqual(
            list_response.data["data"][0]["subject"], "Cần hỗ trợ đổi email"
        )

    def test_user_cannot_read_other_user_ticket(self):
        ticket = SupportTicket.objects.create(
            user=self.other_user,
            subject="Ticket của người khác",
            description="Không được xem.",
            category=SupportTicket.Category.OTHER,
        )

        response = self.client.get(
            reverse("support:ticket-detail", kwargs={"pk": ticket.id})
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["code"], ResponseCode.NOT_FOUND.value)

    def test_user_can_reply_to_own_ticket(self):
        ticket = SupportTicket.objects.create(
            user=self.user,
            subject="Cần hỗ trợ",
            description="Mô tả ban đầu.",
            category=SupportTicket.Category.TECHNICAL,
            status=SupportTicket.TicketStatus.IN_PROGRESS,
        )

        response = self.client.post(
            reverse("support:ticket-message-create", kwargs={"pk": ticket.id}),
            {"content": "Tôi vẫn cần hỗ trợ thêm."},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["code"], ResponseCode.CREATED.value)
        self.assertEqual(
            response.data["data"]["status"], SupportTicket.TicketStatus.IN_PROGRESS
        )
        self.assertEqual(
            response.data["data"]["messages"][0]["content"], "Tôi vẫn cần hỗ trợ thêm."
        )

    def test_user_cannot_reply_to_resolved_ticket(self):
        ticket = SupportTicket.objects.create(
            user=self.user,
            subject="Đã xử lý",
            description="Mô tả ban đầu.",
            category=SupportTicket.Category.TECHNICAL,
            status=SupportTicket.TicketStatus.RESOLVED,
        )

        response = self.client.post(
            reverse("support:ticket-message-create", kwargs={"pk": ticket.id}),
            {"content": "Tôi vẫn cần hỗ trợ thêm."},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], ResponseCode.VALIDATION_ERROR.value)
        self.assertEqual(SupportMessage.objects.count(), 0)
