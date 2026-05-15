from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.events.models import Event, EventCategory
from apps.moderation.models import ModerationLog
from common.response_codes import ResponseCode


class AdminCategoryEventApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.admin_user = user_model.objects.create_user(
            username="phase2_admin",
            email="phase2_admin@example.com",
            password="AdminPass123!",
            is_staff=True,
            is_superuser=True,
        )
        cls.regular_user = user_model.objects.create_user(
            username="phase2_user",
            email="phase2_user@example.com",
            password="UserPass123!",
        )
        cls.category = EventCategory.objects.create(
            name="Workshop",
            slug="workshop",
            description="Workshop events",
            icon="graduation-cap",
            color="#3B82F6",
        )
        cls.empty_category = EventCategory.objects.create(
            name="Empty Category",
            slug="empty-category",
        )
        now = timezone.now()
        cls.event = Event.objects.create(
            category=cls.category,
            created_by=cls.regular_user,
            title="Career Workshop",
            slug="career-workshop-phase2",
            description="Career development event",
            status=Event.Status.PENDING,
            visibility=Event.Visibility.PUBLIC,
            registration_open_at=now - timedelta(days=1),
            registration_close_at=now + timedelta(days=1),
            start_at=now + timedelta(days=3),
            end_at=now + timedelta(days=3, hours=2),
            max_capacity=50,
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

    def test_category_list_create_detail_update_statistics(self):
        self.authenticate_admin()

        list_response = self.client.get(reverse("system_admin:category-list"))
        self.assert_success_envelope(list_response)
        self.assertIn("pagination", list_response.data["meta"])
        self.assertGreaterEqual(list_response.data["meta"]["pagination"]["count"], 2)

        create_response = self.client.post(
            reverse("system_admin:category-list"),
            {
                "name": "Technology",
                "description": "Technology events",
                "icon": "cpu",
                "color": "#06B6D4",
                "is_active": True,
            },
            format="json",
        )
        self.assert_success_envelope(
            create_response,
            expected_status=201,
            expected_code=ResponseCode.CREATED.value,
        )
        category_id = create_response.data["data"]["id"]
        self.assertEqual(create_response.data["data"]["slug"], "technology")

        detail_response = self.client.get(reverse("system_admin:category-detail", kwargs={"pk": category_id}))
        self.assert_success_envelope(detail_response)
        self.assertEqual(detail_response.data["data"]["name"], "Technology")

        update_response = self.client.patch(
            reverse("system_admin:category-detail", kwargs={"pk": category_id}),
            {"description": "Updated technology events", "is_active": False},
            format="json",
        )
        self.assert_success_envelope(update_response)
        self.assertFalse(update_response.data["data"]["is_active"])

        stats_response = self.client.get(reverse("system_admin:category-statistics"))
        self.assert_success_envelope(stats_response)
        self.assertIn("total_categories", stats_response.data["data"])
        self.assertIn("popular_category", stats_response.data["data"])

    def test_category_duplicate_slug_returns_validation_error(self):
        self.authenticate_admin()

        response = self.client.post(
            reverse("system_admin:category-list"),
            {"name": "Duplicate Workshop", "slug": self.category.slug},
            format="json",
        )

        self.assert_error_envelope(
            response,
            expected_status=400,
            expected_code=ResponseCode.API_ERROR.value,
        )
        self.assertIn("slug", response.data["errors"])

    def test_delete_category_with_events_deactivates_instead_of_soft_delete(self):
        self.authenticate_admin()

        response = self.client.delete(
            reverse("system_admin:category-detail", kwargs={"pk": self.category.pk}),
            {"reason": "No longer accepting new events."},
            format="json",
        )

        self.assert_success_envelope(response, expected_code=ResponseCode.DELETED.value)
        self.category.refresh_from_db()
        self.assertFalse(self.category.is_active)
        self.assertIsNone(self.category.deleted_at)

    def test_delete_category_without_events_soft_deletes(self):
        self.authenticate_admin()

        response = self.client.delete(reverse("system_admin:category-detail", kwargs={"pk": self.empty_category.pk}))

        self.assert_success_envelope(response, expected_code=ResponseCode.DELETED.value)
        deleted = EventCategory.all_objects.get(pk=self.empty_category.pk)
        self.assertIsNotNone(deleted.deleted_at)

    def test_category_non_admin_and_anonymous_are_blocked(self):
        response = self.client.get(reverse("system_admin:category-list"))
        self.assert_error_envelope(
            response,
            expected_status=401,
            expected_code=ResponseCode.UNAUTHORIZED.value,
        )

        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get(reverse("system_admin:category-list"))
        self.assert_error_envelope(
            response,
            expected_status=403,
            expected_code=ResponseCode.FORBIDDEN.value,
        )

    def test_event_list_detail_statistics_and_moderation_endpoints(self):
        self.authenticate_admin()
        ModerationLog.objects.create(
            event=self.event,
            admin_user=self.admin_user,
            action=ModerationLog.Action.ESCALATE,
            report_type="safety",
            reason="Capacity needs review.",
        )
        manual_review_event = Event.objects.create(
            category=self.category,
            created_by=self.regular_user,
            title="Manual Review Workshop",
            slug="manual-review-workshop-phase2",
            description="Manual review should not be counted as a user report.",
            status=Event.Status.APPROVED,
            visibility=Event.Visibility.PUBLIC,
            registration_open_at=timezone.now() - timedelta(days=1),
            registration_close_at=timezone.now() + timedelta(days=1),
            start_at=timezone.now() + timedelta(days=4),
            end_at=timezone.now() + timedelta(days=4, hours=2),
            max_capacity=40,
        )
        ModerationLog.objects.create(
            event=manual_review_event,
            admin_user=self.admin_user,
            action=ModerationLog.Action.ESCALATE,
            report_type="manual_review",
            reason="Internal manual review note.",
        )

        list_response = self.client.get(
            reverse("system_admin:event-list"),
            {"status": Event.Status.PENDING, "search": "Career"},
        )
        self.assert_success_envelope(list_response)
        self.assertEqual(list_response.data["data"][0]["id"], str(self.event.id))
        self.assertEqual(list_response.data["data"][0]["latest_report_type"], "safety")

        reported_response = self.client.get(reverse("system_admin:event-list"), {"reported": "true"})
        self.assert_success_envelope(reported_response)
        self.assertEqual(reported_response.data["data"][0]["id"], str(self.event.id))
        self.assertEqual(reported_response.data["meta"]["pagination"]["count"], 1)
        self.assertNotIn(str(manual_review_event.id), {item["id"] for item in reported_response.data["data"]})

        detail_response = self.client.get(reverse("system_admin:event-detail", kwargs={"pk": self.event.pk}))
        self.assert_success_envelope(detail_response)
        self.assertEqual(detail_response.data["data"]["title"], self.event.title)
        self.assertGreaterEqual(len(detail_response.data["data"]["moderation_logs"]), 1)

        stats_response = self.client.get(reverse("system_admin:event-statistics"))
        self.assert_success_envelope(stats_response)
        self.assertGreaterEqual(stats_response.data["data"]["pending_approval"], 1)
        self.assertGreaterEqual(stats_response.data["data"]["reported_events"], 1)

        pulse_response = self.client.get(reverse("system_admin:event-moderation-pulse"))
        self.assert_success_envelope(pulse_response)
        self.assertIn("queue_size", pulse_response.data["data"])

        activities_response = self.client.get(reverse("system_admin:event-moderation-activities"))
        self.assert_success_envelope(activities_response)
        self.assertGreaterEqual(len(activities_response.data["data"]), 1)

        handbook_response = self.client.get(reverse("system_admin:event-policy-handbook"))
        self.assert_success_envelope(handbook_response)
        self.assertIn("cta_label", handbook_response.data["data"])

    def test_event_status_update_creates_moderation_log(self):
        self.authenticate_admin()

        response = self.client.patch(
            reverse("system_admin:event-status", kwargs={"pk": self.event.pk}),
            {"status": Event.Status.APPROVED, "reason": "All requirements met."},
            format="json",
        )

        self.assert_success_envelope(response)
        self.event.refresh_from_db()
        self.assertEqual(self.event.status, Event.Status.APPROVED)
        self.assertTrue(
            ModerationLog.objects.filter(
                event=self.event,
                action=ModerationLog.Action.APPROVE,
                reason="All requirements met.",
            ).exists()
        )

    def test_event_delete_soft_deletes_and_logs_moderation(self):
        self.authenticate_admin()

        response = self.client.delete(
            reverse("system_admin:event-detail", kwargs={"pk": self.event.pk}),
            {"reason": "Invalid event."},
            format="json",
        )

        self.assert_success_envelope(response, expected_code=ResponseCode.DELETED.value)
        deleted_event = Event.all_objects.get(pk=self.event.pk)
        self.assertIsNotNone(deleted_event.deleted_at)
        self.assertTrue(
            ModerationLog.all_objects.filter(event=deleted_event, action=ModerationLog.Action.DELETE).exists()
        )

    def test_event_non_admin_and_anonymous_are_blocked(self):
        response = self.client.get(reverse("system_admin:event-list"))
        self.assert_error_envelope(
            response,
            expected_status=401,
            expected_code=ResponseCode.UNAUTHORIZED.value,
        )

        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get(reverse("system_admin:event-list"))
        self.assert_error_envelope(
            response,
            expected_status=403,
            expected_code=ResponseCode.FORBIDDEN.value,
        )
