from datetime import timedelta
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.notifications.models import Notification, NotificationRecipient
from apps.system_admin.services.notification_services import AdminNotificationService
from apps.support.models import (
    LegalDocument,
    SupportArticle,
    SupportMessage,
    SupportTicket,
)
from common.response_codes import ResponseCode


class AdminSupportNotificationApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.admin_user = user_model.objects.create_user(
            username="phase3_admin",
            email="phase3_admin@example.com",
            password="AdminPass123!",
            is_staff=True,
            is_superuser=True,
        )
        cls.staff_user = user_model.objects.create_user(
            username="phase3_staff",
            email="phase3_staff@example.com",
            password="StaffPass123!",
            is_staff=True,
        )
        cls.regular_user = user_model.objects.create_user(
            username="phase3_user",
            email="phase3_user@example.com",
            password="UserPass123!",
            full_name="Người dùng Phase 3",
        )
        cls.ticket = SupportTicket.objects.create(
            user=cls.regular_user,
            subject="Không nhận được vé",
            description="Tôi đã đăng ký nhưng chưa thấy vé.",
            category=SupportTicket.Category.TECHNICAL,
            priority=SupportTicket.TicketPriority.MEDIUM,
            status=SupportTicket.TicketStatus.OPEN,
        )
        SupportMessage.objects.create(
            ticket=cls.ticket,
            author_user=cls.regular_user,
            content="Tôi cần kiểm tra vé đã đăng ký.",
            is_staff=False,
        )
        cls.notification = Notification.objects.create(
            created_by=cls.admin_user,
            title="Thông báo bảo trì",
            message="Hệ thống sẽ bảo trì vào tối nay.",
            audience_type=Notification.AudienceType.ALL,
            type=Notification.NotificationType.ANNOUNCEMENT,
            status=Notification.NotificationStatus.DRAFT,
        )

    def setUp(self):
        self.client = APIClient()

    def authenticate_admin(self):
        self.client.force_authenticate(user=self.admin_user)

    def assert_success_envelope(
        self, response, *, expected_status=200, expected_code=ResponseCode.SUCCESS.value
    ):
        self.assertEqual(response.status_code, expected_status)
        self.assertEqual(
            set(response.data.keys()),
            {"success", "code", "message", "data", "errors", "meta"},
        )
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["code"], expected_code)
        self.assertIsNone(response.data["errors"])

    def assert_error_envelope(self, response, *, expected_status, expected_code=None):
        self.assertEqual(response.status_code, expected_status)
        self.assertEqual(
            set(response.data.keys()),
            {"success", "code", "message", "data", "errors", "meta"},
        )
        self.assertFalse(response.data["success"])
        if expected_code is not None:
            self.assertEqual(response.data["code"], expected_code)

    def test_support_ticket_workflow(self):
        self.authenticate_admin()

        list_response = self.client.get(
            reverse("system_admin:support-ticket-list"), {"status": "open"}
        )
        self.assert_success_envelope(list_response)
        self.assertIn("pagination", list_response.data["meta"])
        self.assertEqual(list_response.data["data"][0]["id"], str(self.ticket.id))

        detail_response = self.client.get(
            reverse("system_admin:support-ticket-detail", kwargs={"pk": self.ticket.pk})
        )
        self.assert_success_envelope(detail_response)
        self.assertEqual(detail_response.data["data"]["subject"], self.ticket.subject)
        self.assertGreaterEqual(len(detail_response.data["data"]["messages"]), 1)

        reply_response = self.client.post(
            reverse(
                "system_admin:support-ticket-messages", kwargs={"pk": self.ticket.pk}
            ),
            {"content": "Quản trị viên đang kiểm tra yêu cầu của bạn."},
            format="json",
        )
        self.assert_success_envelope(reply_response)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, SupportTicket.TicketStatus.IN_PROGRESS)
        self.assertTrue(self.ticket.messages.filter(is_staff=True).exists())

        update_response = self.client.patch(
            reverse(
                "system_admin:support-ticket-detail", kwargs={"pk": self.ticket.pk}
            ),
            {"assigned_to": str(self.staff_user.pk), "priority": "high"},
            format="json",
        )
        self.assert_success_envelope(update_response)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.assigned_to_id, self.staff_user.pk)
        self.assertEqual(self.ticket.priority, SupportTicket.TicketPriority.HIGH)

        escalate_response = self.client.post(
            reverse(
                "system_admin:support-ticket-escalate", kwargs={"pk": self.ticket.pk}
            ),
            {"reason": "Cần ưu tiên xử lý."},
            format="json",
        )
        self.assert_success_envelope(escalate_response)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.priority, SupportTicket.TicketPriority.URGENT)

        resolve_response = self.client.post(
            reverse(
                "system_admin:support-ticket-resolve", kwargs={"pk": self.ticket.pk}
            ),
            {"note": "Yêu cầu đã được xử lý."},
            format="json",
        )
        self.assert_success_envelope(resolve_response)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, SupportTicket.TicketStatus.RESOLVED)

        stats_response = self.client.get(
            reverse("system_admin:support-ticket-statistics")
        )
        self.assert_success_envelope(stats_response)
        self.assertIn("avg_response_minutes", stats_response.data["data"])

    def test_support_validates_assignee_and_permissions(self):
        self.authenticate_admin()
        response = self.client.patch(
            reverse(
                "system_admin:support-ticket-detail", kwargs={"pk": self.ticket.pk}
            ),
            {"assigned_to": str(self.regular_user.pk)},
            format="json",
        )
        self.assert_error_envelope(response, expected_status=400)

        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get(reverse("system_admin:support-ticket-list"))
        self.assert_error_envelope(
            response,
            expected_status=403,
            expected_code=ResponseCode.FORBIDDEN.value,
        )

        self.client.force_authenticate(user=None)
        response = self.client.get(reverse("system_admin:support-ticket-list"))
        self.assert_error_envelope(
            response,
            expected_status=401,
            expected_code=ResponseCode.UNAUTHORIZED.value,
        )

    def test_help_center_content_admin_workflow(self):
        self.authenticate_admin()

        category_response = self.client.post(
            reverse("system_admin:support-help-category-list"),
            {
                "name": "Tài khoản",
                "slug": "tai-khoan",
                "description": "Câu hỏi về tài khoản",
                "sort_order": 1,
                "is_active": True,
            },
            format="json",
        )
        self.assert_success_envelope(
            category_response,
            expected_status=201,
            expected_code=ResponseCode.CREATED.value,
        )
        category_id = category_response.data["data"]["id"]

        article_response = self.client.post(
            reverse("system_admin:support-help-article-list"),
            {
                "category_id": category_id,
                "title": "Làm sao đổi email?",
                "slug": "doi-email",
                "summary": "Hướng dẫn đổi email tài khoản.",
                "body": "Mở Chỉnh sửa hồ sơ và chọn Đổi email.",
                "locale": "vi",
                "status": SupportArticle.ArticleStatus.DRAFT,
                "sort_order": 1,
            },
            format="json",
        )
        self.assert_success_envelope(
            article_response,
            expected_status=201,
            expected_code=ResponseCode.CREATED.value,
        )
        article_id = article_response.data["data"]["id"]

        publish_response = self.client.post(
            reverse(
                "system_admin:support-help-article-publish", kwargs={"pk": article_id}
            )
        )
        self.assert_success_envelope(publish_response)
        self.assertEqual(
            publish_response.data["data"]["status"],
            SupportArticle.ArticleStatus.PUBLISHED,
        )
        self.assertIsNotNone(publish_response.data["data"]["published_at"])

        list_response = self.client.get(
            reverse("system_admin:support-help-article-list"),
            {"status": SupportArticle.ArticleStatus.PUBLISHED, "locale": "vi"},
        )
        self.assert_success_envelope(list_response)
        self.assertEqual(list_response.data["data"][0]["id"], article_id)

        archive_response = self.client.post(
            reverse(
                "system_admin:support-help-article-archive", kwargs={"pk": article_id}
            )
        )
        self.assert_success_envelope(archive_response)
        self.assertEqual(
            archive_response.data["data"]["status"],
            SupportArticle.ArticleStatus.ARCHIVED,
        )

    def test_legal_document_admin_workflow(self):
        self.authenticate_admin()

        create_response = self.client.post(
            reverse("system_admin:support-legal-document-list"),
            {
                "document_type": LegalDocument.DocumentType.PRIVACY_POLICY,
                "title": "Chính sách quyền riêng tư",
                "version": "2026-05",
                "summary": "Cách UEvents xử lý dữ liệu cá nhân.",
                "body": "Nội dung chính sách quyền riêng tư.",
                "locale": "vi",
                "status": LegalDocument.DocumentStatus.DRAFT,
            },
            format="json",
        )
        self.assert_success_envelope(
            create_response,
            expected_status=201,
            expected_code=ResponseCode.CREATED.value,
        )
        document_id = create_response.data["data"]["id"]

        publish_response = self.client.post(
            reverse(
                "system_admin:support-legal-document-publish",
                kwargs={"pk": document_id},
            )
        )
        self.assert_success_envelope(publish_response)
        self.assertEqual(
            publish_response.data["data"]["status"],
            LegalDocument.DocumentStatus.PUBLISHED,
        )
        self.assertIsNotNone(publish_response.data["data"]["published_at"])

        list_response = self.client.get(
            reverse("system_admin:support-legal-document-list"),
            {
                "document_type": LegalDocument.DocumentType.PRIVACY_POLICY,
                "status": LegalDocument.DocumentStatus.PUBLISHED,
                "locale": "vi",
            },
        )
        self.assert_success_envelope(list_response)
        self.assertEqual(list_response.data["data"][0]["id"], document_id)

        archive_response = self.client.post(
            reverse(
                "system_admin:support-legal-document-archive",
                kwargs={"pk": document_id},
            )
        )
        self.assert_success_envelope(archive_response)
        self.assertEqual(
            archive_response.data["data"]["status"],
            LegalDocument.DocumentStatus.ARCHIVED,
        )

    def test_notification_workflow_publish_export_and_constraints(self):
        self.authenticate_admin()

        create_response = self.client.post(
            reverse("system_admin:notification-list"),
            {
                "title": "Nhắc lịch sự kiện",
                "message": "Đừng quên tham gia sự kiện đã đăng ký.",
                "type": "reminder",
                "audience_type": "students",
            },
            format="json",
        )
        self.assert_success_envelope(
            create_response,
            expected_status=201,
            expected_code=ResponseCode.CREATED.value,
        )
        notification_id = create_response.data["data"]["id"]

        patch_response = self.client.patch(
            reverse("system_admin:notification-detail", kwargs={"pk": notification_id}),
            {"title": "Nhắc lịch tham gia sự kiện"},
            format="json",
        )
        self.assert_success_envelope(patch_response)
        self.assertEqual(
            patch_response.data["data"]["title"], "Nhắc lịch tham gia sự kiện"
        )

        publish_response = self.client.post(
            reverse(
                "system_admin:notification-publish", kwargs={"pk": notification_id}
            ),
            format="json",
        )
        self.assert_success_envelope(publish_response)
        self.assertEqual(
            publish_response.data["data"]["status"],
            Notification.NotificationStatus.SENT,
        )
        self.assertTrue(
            NotificationRecipient.objects.filter(
                notification_id=notification_id
            ).exists()
        )
        self.assertTrue(
            NotificationRecipient.objects.filter(
                notification_id=notification_id,
                delivery_status=NotificationRecipient.DeliveryStatus.QUEUED,
            ).exists()
        )

        blocked_patch = self.client.patch(
            reverse("system_admin:notification-detail", kwargs={"pk": notification_id}),
            {"title": "Không được sửa"},
            format="json",
        )
        self.assert_error_envelope(blocked_patch, expected_status=400)

        blocked_delete = self.client.delete(
            reverse("system_admin:notification-detail", kwargs={"pk": notification_id})
        )
        self.assert_error_envelope(blocked_delete, expected_status=400)

        export_response = self.client.get(reverse("system_admin:notification-export"))
        self.assertEqual(export_response.status_code, 200)
        self.assertIn("text/csv", export_response["Content-Type"])

        excel_response = self.client.get(
            reverse("system_admin:notification-export"), {"export_format": "xlsx"}
        )
        self.assertEqual(excel_response.status_code, 200)
        self.assertIn(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            excel_response["Content-Type"],
        )
        self.assertIn(".xlsx", excel_response["Content-Disposition"])

    def test_notification_scheduled_statistics_and_permissions(self):
        self.authenticate_admin()
        scheduled_at = timezone.now() + timedelta(days=1)
        response = self.client.post(
            reverse("system_admin:notification-list"),
            {
                "title": "Thông báo lên lịch",
                "message": "Nội dung thông báo đã lên lịch.",
                "status": "scheduled",
                "scheduled_at": scheduled_at.isoformat(),
            },
            format="json",
        )
        self.assert_success_envelope(
            response, expected_status=201, expected_code=ResponseCode.CREATED.value
        )

        stats_response = self.client.get(
            reverse("system_admin:notification-statistics")
        )
        self.assert_success_envelope(stats_response)
        self.assertGreaterEqual(stats_response.data["data"]["scheduled"], 1)

        config_response = self.client.get(
            reverse("system_admin:notification-pagination-config")
        )
        self.assert_success_envelope(config_response)
        self.assertEqual(config_response.data["data"]["per_page"], 10)

        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get(reverse("system_admin:notification-list"))
        self.assert_error_envelope(
            response,
            expected_status=403,
            expected_code=ResponseCode.FORBIDDEN.value,
        )

    def test_notification_rejects_past_schedule_time(self):
        self.authenticate_admin()
        past_scheduled_at = timezone.now() - timedelta(days=1)

        create_response = self.client.post(
            reverse("system_admin:notification-list"),
            {
                "title": "Thông báo sai thời gian",
                "message": "Không được lên lịch thông báo trong quá khứ.",
                "status": "scheduled",
                "scheduled_at": past_scheduled_at.isoformat(),
            },
            format="json",
        )
        self.assert_error_envelope(create_response, expected_status=400)

        draft_response = self.client.post(
            reverse("system_admin:notification-list"),
            {
                "title": "Bản nháp cần kiểm tra",
                "message": "Nội dung bản nháp dùng để kiểm tra cập nhật lịch gửi.",
            },
            format="json",
        )
        self.assert_success_envelope(
            draft_response,
            expected_status=201,
            expected_code=ResponseCode.CREATED.value,
        )

        patch_response = self.client.patch(
            reverse(
                "system_admin:notification-detail",
                kwargs={"pk": draft_response.data["data"]["id"]},
            ),
            {
                "status": "scheduled",
                "scheduled_at": past_scheduled_at.isoformat(),
            },
            format="json",
        )
        self.assert_error_envelope(patch_response, expected_status=400)

    def test_due_scheduled_notifications_are_published_by_scheduler_service(self):
        due_notification = Notification.objects.create(
            created_by=self.admin_user,
            title="Thông báo đến giờ gửi",
            message="Thông báo này phải được gửi bởi scheduler.",
            audience_type=Notification.AudienceType.ALL,
            type=Notification.NotificationType.ANNOUNCEMENT,
            status=Notification.NotificationStatus.SCHEDULED,
            scheduled_at=timezone.now() - timedelta(minutes=1),
        )
        future_notification = Notification.objects.create(
            created_by=self.admin_user,
            title="Thông báo chưa đến giờ",
            message="Thông báo này chưa được gửi.",
            audience_type=Notification.AudienceType.ALL,
            type=Notification.NotificationType.ANNOUNCEMENT,
            status=Notification.NotificationStatus.SCHEDULED,
            scheduled_at=timezone.now() + timedelta(hours=1),
        )

        result = AdminNotificationService.publish_due_scheduled_notifications(
            batch_size=10
        )

        self.assertEqual(result["published_count"], 1)
        self.assertEqual(result["remaining_due"], 0)
        due_notification.refresh_from_db()
        future_notification.refresh_from_db()
        self.assertEqual(due_notification.status, Notification.NotificationStatus.SENT)
        self.assertIsNotNone(due_notification.sent_at)
        self.assertTrue(
            NotificationRecipient.objects.filter(notification=due_notification).exists()
        )
        self.assertTrue(
            NotificationRecipient.objects.filter(
                notification=due_notification,
                delivery_status=NotificationRecipient.DeliveryStatus.QUEUED,
            ).exists()
        )
        self.assertEqual(
            future_notification.status, Notification.NotificationStatus.SCHEDULED
        )
        self.assertFalse(
            NotificationRecipient.objects.filter(
                notification=future_notification
            ).exists()
        )

    def test_publish_scheduled_notifications_command(self):
        due_notification = Notification.objects.create(
            created_by=self.admin_user,
            title="Thông báo command",
            message="Thông báo này được gửi bởi management command.",
            audience_type=Notification.AudienceType.ALL,
            type=Notification.NotificationType.ANNOUNCEMENT,
            status=Notification.NotificationStatus.SCHEDULED,
            scheduled_at=timezone.now() - timedelta(minutes=1),
        )
        output = StringIO()

        call_command("publish_scheduled_notifications", batch_size=100, stdout=output)

        due_notification.refresh_from_db()
        self.assertEqual(due_notification.status, Notification.NotificationStatus.SENT)
        self.assertIn("Đã gửi 1 thông báo đến hạn", output.getvalue())
