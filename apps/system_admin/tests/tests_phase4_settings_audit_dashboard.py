from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.app_settings.models import AppSetting
from apps.events.models import Event, EventCategory
from apps.registrations.models import EventRegistration
from apps.support.models import SupportTicket
from common.response_codes import ResponseCode


class AdminPhase4SettingsAuditDashboardTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.admin_user = user_model.objects.create_user(
            username="phase4_admin",
            email="phase4_admin@example.com",
            password="AdminPass123!",
            full_name="Quản trị Phase 4",
            is_staff=True,
            is_superuser=True,
        )
        cls.staff_user = user_model.objects.create_user(
            username="phase4_staff",
            email="phase4_staff@example.com",
            password="StaffPass123!",
            is_staff=True,
        )
        cls.regular_user = user_model.objects.create_user(
            username="phase4_user",
            email="phase4_user@example.com",
            password="UserPass123!",
        )
        cls.category = EventCategory.objects.create(name="Phase 4", slug="phase-4")
        cls.event = Event.objects.create(
            category=cls.category,
            created_by=cls.regular_user,
            title="Sự kiện Phase 4",
            slug="phase-4-event",
            description="Dữ liệu kiểm tra dashboard.",
            status=Event.Status.PENDING,
            start_at=timezone.now() + timedelta(days=3),
            end_at=timezone.now() + timedelta(days=3, hours=2),
        )
        EventRegistration.objects.create(event=cls.event, user=cls.regular_user)
        SupportTicket.objects.create(
            user=cls.regular_user,
            subject="Cần hỗ trợ Phase 4",
            description="Ticket dùng cho dashboard.",
            status=SupportTicket.TicketStatus.OPEN,
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

    def test_settings_read_update_and_protected_key(self):
        self.authenticate_admin()

        list_response = self.client.get(reverse("system_admin:settings"))
        self.assert_success_envelope(list_response)
        self.assertIn("groups", list_response.data["data"])
        self.assertIn("settings", list_response.data["data"])

        update_response = self.client.patch(
            reverse("system_admin:settings"),
            {
                "settings": [
                    {"key": "appearance.dark_mode", "value": False},
                    {"key": "audit.alerts_enabled", "value": True},
                ],
                "reason": "Cập nhật kiểm thử Phase 4.",
            },
            format="json",
        )
        self.assert_success_envelope(update_response)
        stored = AppSetting.objects.get(key="appearance.dark_mode")
        self.assertEqual(stored.value, "false")
        self.assertEqual(stored.updated_by, self.admin_user)

        protected_response = self.client.patch(
            reverse("system_admin:settings"),
            {"settings": [{"key": "audit.export_requires_date_range", "value": False}]},
            format="json",
        )
        self.assert_error_envelope(protected_response, expected_status=400)

    @patch("apps.system_admin.services.audit_log_services.OpenSearchAuditClient.search")
    def test_audit_log_list_export_and_permission(self, search_mock):
        now = timezone.now()
        search_mock.return_value = {
            "hits": {
                "total": {"value": 1},
                "hits": [
                    {
                        "_id": "audit-1",
                        "_source": {
                            "event_time": now.isoformat(),
                            "actor_id": str(self.admin_user.id),
                            "action_type": "update_settings",
                            "target_type": "app_settings.AppSetting",
                            "target_id": "appearance.dark_mode",
                            "reason": "Kiểm thử",
                            "level": "INFO",
                            "status": "success",
                            "system_module": "system_admin",
                            "trace_id": "trace-1",
                            "metadata": {"updated_keys": ["appearance.dark_mode"]},
                        },
                    }
                ],
            }
        }
        self.authenticate_admin()

        list_response = self.client.get(
            reverse("system_admin:audit-log-list"),
            {
                "date_from": (now - timedelta(days=1)).isoformat(),
                "date_to": now.isoformat(),
                "action_type": "update_settings",
            },
        )
        self.assert_success_envelope(list_response)
        self.assertEqual(list_response.data["data"][0]["action_type"], "update_settings")
        self.assertEqual(list_response.data["data"][0]["actor"]["name"], self.admin_user.full_name)
        self.assertEqual(list_response.data["data"][0]["actor"]["username"], self.admin_user.username)
        self.assertEqual(list_response.data["data"][0]["actor"]["email"], self.admin_user.email)
        self.assertIn("pagination", list_response.data["meta"])

        export_response = self.client.get(
            reverse("system_admin:audit-log-export"),
            {
                "date_from": (now - timedelta(days=1)).isoformat(),
                "date_to": now.isoformat(),
            },
        )
        self.assertEqual(export_response.status_code, 200)
        self.assertIn("text/csv", export_response["Content-Type"])

        self.client.force_authenticate(user=self.staff_user)
        denied_response = self.client.get(reverse("system_admin:audit-log-list"))
        self.assert_error_envelope(
            denied_response,
            expected_status=403,
            expected_code=ResponseCode.FORBIDDEN.value,
        )

    def test_audit_export_requires_date_range(self):
        self.authenticate_admin()

        response = self.client.get(reverse("system_admin:audit-log-export"))

        self.assert_error_envelope(response, expected_status=400)

    @patch("apps.system_admin.services.audit_log_services.OpenSearchAuditClient.search")
    def test_dashboard_overview_uses_real_domain_counts(self, search_mock):
        search_mock.return_value = {"hits": {"total": {"value": 0}, "hits": []}}
        self.authenticate_admin()

        overview_response = self.client.get(reverse("system_admin:dashboard-overview"))

        self.assert_success_envelope(overview_response)
        self.assertIn("stats", overview_response.data["data"])
        self.assertIn("growth_series", overview_response.data["data"])
        self.assertIn("queue", overview_response.data["data"])
        stat_ids = {item["id"] for item in overview_response.data["data"]["stats"]}
        self.assertTrue({"users", "events", "registrations", "support"}.issubset(stat_ids))

        self.client.force_authenticate(user=self.regular_user)
        denied_response = self.client.get(reverse("system_admin:dashboard-overview"))
        self.assert_error_envelope(
            denied_response,
            expected_status=403,
            expected_code=ResponseCode.FORBIDDEN.value,
        )
