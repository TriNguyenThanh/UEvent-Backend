from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.events.models import Event, EventCategory
from apps.registrations.models import EventRegistration, Ticket
from apps.registrations.services import build_qr_payload, sign_qr_payload
from common.response_codes import ResponseCode


class AdminTicketApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.admin_user = user_model.objects.create_user(
            username="ticket_admin",
            email="ticket_admin@example.com",
            password="AdminPass123!",
            is_staff=True,
            is_superuser=True,
        )
        cls.regular_user = user_model.objects.create_user(
            username="ticket_user",
            email="ticket_user@example.com",
            password="UserPass123!",
            full_name="Người dùng vé",
        )
        cls.category = EventCategory.objects.create(name="Ticket", slug="ticket")
        now = timezone.now()
        cls.event = Event.objects.create(
            category=cls.category,
            created_by=cls.regular_user,
            title="Sự kiện check-in",
            slug="ticket-checkin-event",
            description="Sự kiện dùng để kiểm thử vé.",
            status=Event.Status.APPROVED,
            visibility=Event.Visibility.PUBLIC,
            registration_open_at=now - timedelta(days=1),
            registration_close_at=now + timedelta(days=1),
            start_at=now - timedelta(minutes=30),
            end_at=now + timedelta(hours=2),
            max_capacity=100,
        )
        cls.registration = EventRegistration.objects.create(
            event=cls.event,
            user=cls.regular_user,
            status=EventRegistration.RegistrationStatus.REGISTERED,
        )
        payload = build_qr_payload("TK-ADMIN-001")
        cls.ticket = Ticket.objects.create(
            registration=cls.registration,
            ticket_code="TK-ADMIN-001",
            qr_payload=payload,
            qr_signature=sign_qr_payload(payload),
            status=Ticket.TicketStatus.VALID,
            expires_at=cls.event.end_at,
        )

    def setUp(self):
        self.client = APIClient()

    def authenticate_admin(self):
        self.client.force_authenticate(user=self.admin_user)

    def assert_success_envelope(self, response, *, expected_status=200, expected_code=ResponseCode.SUCCESS.value):
        self.assertEqual(response.status_code, expected_status)
        self.assertEqual(set(response.data.keys()), {"success", "code", "message", "data", "errors", "meta"})
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["code"], expected_code)
        self.assertIsNone(response.data["errors"])

    def assert_error_envelope(self, response, *, expected_status, expected_code=None):
        self.assertEqual(response.status_code, expected_status)
        self.assertEqual(set(response.data.keys()), {"success", "code", "message", "data", "errors", "meta"})
        self.assertFalse(response.data["success"])
        if expected_code is not None:
            self.assertEqual(response.data["code"], expected_code)

    def create_ticket(self, code):
        user_model = get_user_model()
        user = user_model.objects.create_user(
            username=f"user_{code.lower().replace('-', '_')}",
            email=f"{code.lower()}@example.com",
            password="UserPass123!",
        )
        registration = EventRegistration.objects.create(
            event=self.event,
            user=user,
            status=EventRegistration.RegistrationStatus.REGISTERED,
        )
        payload = build_qr_payload(code)
        return Ticket.objects.create(
            registration=registration,
            ticket_code=code,
            qr_payload=payload,
            qr_signature=sign_qr_payload(payload),
            status=Ticket.TicketStatus.VALID,
            expires_at=self.event.end_at,
        )

    def test_ticket_list_detail_statistics_and_export(self):
        self.authenticate_admin()

        list_response = self.client.get(reverse("system_admin:ticket-list"), {"search": "TK-ADMIN-001"})
        self.assert_success_envelope(list_response)
        self.assertIn("pagination", list_response.data["meta"])
        self.assertEqual(list_response.data["data"][0]["ticket_code"], self.ticket.ticket_code)
        self.assertEqual(list_response.data["data"][0]["event"]["id"], str(self.event.id))

        detail_response = self.client.get(reverse("system_admin:ticket-detail", kwargs={"pk": self.ticket.pk}))
        self.assert_success_envelope(detail_response)
        self.assertEqual(detail_response.data["data"]["user"]["email"], self.regular_user.email)

        stats_response = self.client.get(reverse("system_admin:ticket-statistics"))
        self.assert_success_envelope(stats_response)
        self.assertGreaterEqual(stats_response.data["data"]["total_tickets"], 1)
        self.assertIn("checkin_rate", stats_response.data["data"])

        export_response = self.client.get(reverse("system_admin:ticket-export"), {"export_format": "csv"})
        self.assertEqual(export_response.status_code, 200)
        self.assertIn("text/csv", export_response["Content-Type"])
        self.assertIn("tickets_export", export_response["Content-Disposition"])

    def test_ticket_cancel_updates_registration_and_audits(self):
        self.authenticate_admin()
        ticket = self.create_ticket("TK-CANCEL-001")

        with self.assertLogs("uevent.audit", level="INFO") as logs:
            response = self.client.post(
                reverse("system_admin:ticket-cancel", kwargs={"pk": ticket.pk}),
                {"reason": "Người tham dự yêu cầu hủy."},
                format="json",
            )

        self.assert_success_envelope(response)
        ticket.refresh_from_db()
        ticket.registration.refresh_from_db()
        self.assertEqual(ticket.status, Ticket.TicketStatus.CANCELLED)
        self.assertEqual(ticket.registration.status, EventRegistration.RegistrationStatus.CANCELLED)
        self.assertTrue(any("cancel_ticket" in message for message in logs.output))

    def test_ticket_restore_updates_registration_and_audits(self):
        self.authenticate_admin()
        ticket = self.create_ticket("TK-RESTORE-001")
        ticket.status = Ticket.TicketStatus.CANCELLED
        ticket.save(update_fields=["status", "updated_at"])
        ticket.registration.status = EventRegistration.RegistrationStatus.CANCELLED
        ticket.registration.cancelled_at = timezone.now()
        ticket.registration.cancel_reason = "Người tham dự yêu cầu hủy."
        ticket.registration.save(update_fields=["status", "cancelled_at", "cancel_reason", "updated_at"])

        with self.assertLogs("uevent.audit", level="INFO") as logs:
            response = self.client.post(
                reverse("system_admin:ticket-restore", kwargs={"pk": ticket.pk}),
                {"reason": "Quản trị viên khôi phục vé."},
                format="json",
            )

        self.assert_success_envelope(response)
        ticket.refresh_from_db()
        ticket.registration.refresh_from_db()
        self.assertEqual(ticket.status, Ticket.TicketStatus.VALID)
        self.assertEqual(ticket.registration.status, EventRegistration.RegistrationStatus.REGISTERED)
        self.assertIsNone(ticket.registration.cancelled_at)
        self.assertIsNone(ticket.registration.cancel_reason)
        self.assertTrue(any("restore_ticket" in message for message in logs.output))

    def test_ticket_checkin_scan_success_and_duplicate_log(self):
        self.authenticate_admin()
        ticket = self.create_ticket("TK-SCAN-001")

        with self.assertLogs("uevent.audit", level="INFO") as logs:
            response = self.client.post(
                reverse("system_admin:ticket-checkin-scan"),
                {
                    "event_id": str(self.event.id),
                    "ticket_code": ticket.ticket_code,
                    "note": "Check-in tại cổng chính.",
                },
                format="json",
            )

        self.assert_success_envelope(response)
        self.assertEqual(response.data["data"]["result"], "success")
        ticket.refresh_from_db()
        ticket.registration.refresh_from_db()
        self.assertEqual(ticket.status, Ticket.TicketStatus.USED)
        self.assertEqual(ticket.registration.status, EventRegistration.RegistrationStatus.CHECKED_IN)
        self.assertTrue(any("admin_ticket_checkin_scan" in message for message in logs.output))

        duplicate_response = self.client.post(
            reverse("system_admin:ticket-checkin-scan"),
            {"event_id": str(self.event.id), "ticket_code": ticket.ticket_code},
            format="json",
        )
        self.assert_success_envelope(duplicate_response)
        self.assertEqual(duplicate_response.data["data"]["result"], "already_checked_in")

        logs_response = self.client.get(
            reverse("system_admin:ticket-checkin-list"),
            {"ticket_id": str(ticket.id)},
        )
        self.assert_success_envelope(logs_response)
        self.assertGreaterEqual(logs_response.data["meta"]["pagination"]["count"], 2)

    def test_ticket_scan_supports_signed_qr_payload(self):
        self.authenticate_admin()
        ticket = self.create_ticket("TK-QR-001")

        response = self.client.post(
            reverse("system_admin:ticket-checkin-scan"),
            {
                "event_id": str(self.event.id),
                "qr_payload": ticket.qr_payload,
                "qr_signature": ticket.qr_signature,
            },
            format="json",
        )

        self.assert_success_envelope(response)
        self.assertEqual(response.data["data"]["result"], "success")

    def test_ticket_permissions_block_anonymous_and_regular_user(self):
        response = self.client.get(reverse("system_admin:ticket-list"))
        self.assert_error_envelope(
            response,
            expected_status=401,
            expected_code=ResponseCode.UNAUTHORIZED.value,
        )

        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get(reverse("system_admin:ticket-list"))
        self.assert_error_envelope(
            response,
            expected_status=403,
            expected_code=ResponseCode.FORBIDDEN.value,
        )
