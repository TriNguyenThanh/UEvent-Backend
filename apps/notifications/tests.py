from datetime import datetime, time, timedelta, timezone as datetime_timezone

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.events.models import Event, EventCategory, EventOrganizer
from apps.notifications.action_urls import build_event_action_url
from apps.notifications.models import (
    Notification,
    NotificationPreference,
    NotificationRecipient,
)
from apps.notifications.services.fcm_client import FcmSendResult
from apps.notifications.services.push_delivery_service import (
    PushDeliveryService,
    RetryableFcmDeliveryError,
)
from apps.users.models import UserSession
from common.response_codes import ResponseCode


class NotificationActionUrlTests(TestCase):
    @override_settings(PUBLIC_WEB_BASE_URL="https://uevent.example/")
    def test_build_event_action_url_uses_event_slug(self):
        self.assertEqual(
            build_event_action_url("career-workshop"),
            "https://uevent.example/events/share/career-workshop",
        )


class FakeFcmClient:
    def __init__(self, *, success=True, invalid_token=False, retryable=False):
        self.success = success
        self.invalid_token = invalid_token
        self.retryable = retryable
        self.messages = []

    def send_each(self, *, messages):
        self.messages = list(messages)
        return [
            FcmSendResult(
                token=message["token"],
                success=self.success,
                error_code=self._error_code(),
                error_message="Token không còn hợp lệ." if self.invalid_token else "",
                invalid_token=self.invalid_token,
                retryable=self.retryable,
            )
            for message in self.messages
        ]

    def send_multicast(self, *, tokens, title, body, data):
        return [
            FcmSendResult(
                token=token,
                success=self.success,
                error_code=self._error_code(),
                error_message="Token không còn hợp lệ." if self.invalid_token else "",
                invalid_token=self.invalid_token,
                retryable=self.retryable,
            )
            for token in tokens
        ]

    def _error_code(self) -> str:
        if self.invalid_token:
            return "registration-token-not-registered"
        if self.retryable:
            return "unavailable"
        return ""


class UserNotificationApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.user = user_model.objects.create_user(
            username="mobile_user",
            email="mobile_user@example.com",
            password="UserPass123!",
        )
        cls.other_user = user_model.objects.create_user(
            username="other_mobile_user",
            email="other_mobile_user@example.com",
            password="UserPass123!",
        )
        cls.notification = Notification.objects.create(
            title="Thông báo thật",
            message="Nội dung thông báo gửi đến ứng dụng.",
            type=Notification.NotificationType.ANNOUNCEMENT,
            category=Notification.NotificationCategory.SYSTEM,
            target=Notification.NotificationTarget.NOTIFICATION_DETAIL,
            audience_type=Notification.AudienceType.ALL,
            status=Notification.NotificationStatus.SENT,
            sent_at=timezone.now(),
        )
        cls.recipient = NotificationRecipient.objects.create(
            notification=cls.notification,
            user=cls.user,
            delivery_status=NotificationRecipient.DeliveryStatus.SENT,
            delivered_at=timezone.now(),
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def assert_success_envelope(self, response, *, expected_status=200):
        self.assertEqual(response.status_code, expected_status)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["code"], ResponseCode.SUCCESS.value)

    def test_user_can_list_unread_and_mark_own_notification_read(self):
        list_response = self.client.get(reverse("notifications:notification-list"))
        self.assert_success_envelope(list_response)
        item = list_response.data["data"][0]
        self.assertEqual(item["id"], str(self.recipient.id))
        self.assertEqual(item["recipient_id"], str(self.recipient.id))
        self.assertEqual(
            item["target"], Notification.NotificationTarget.NOTIFICATION_DETAIL
        )

        count_response = self.client.get(
            reverse("notifications:notification-unread-count")
        )
        self.assert_success_envelope(count_response)
        self.assertEqual(count_response.data["data"]["unread_count"], 1)

        read_response = self.client.post(
            reverse(
                "notifications:notification-mark-read", kwargs={"pk": self.recipient.pk}
            )
        )
        self.assert_success_envelope(read_response)
        self.recipient.refresh_from_db()
        self.assertEqual(
            self.recipient.delivery_status, NotificationRecipient.DeliveryStatus.READ
        )
        self.assertIsNotNone(self.recipient.read_at)

    def test_user_can_mark_notification_opened(self):
        response = self.client.post(
            reverse(
                "notifications:notification-mark-opened",
                kwargs={"pk": self.recipient.pk},
            )
        )

        self.assert_success_envelope(response)
        self.recipient.refresh_from_db()
        self.assertIsNotNone(self.recipient.opened_at)
        self.assertIsNotNone(self.recipient.read_at)

    def test_user_cannot_mark_other_user_notification_read(self):
        other_recipient = NotificationRecipient.objects.create(
            notification=self.notification,
            user=self.other_user,
            delivery_status=NotificationRecipient.DeliveryStatus.SENT,
            delivered_at=timezone.now(),
        )

        response = self.client.post(
            reverse(
                "notifications:notification-mark-read",
                kwargs={"pk": other_recipient.pk},
            )
        )

        self.assertEqual(response.status_code, 404)
        other_recipient.refresh_from_db()
        self.assertIsNone(other_recipient.read_at)

    def test_register_and_unregister_device_token(self):
        register_response = self.client.post(
            reverse("notifications:notification-register-device"),
            {"fcm_token": "fcm-token-123", "device_name": "Pixel 8"},
            format="json",
        )
        self.assert_success_envelope(register_response)
        self.assertTrue(
            UserSession.objects.filter(
                user=self.user, fcm_token="fcm-token-123"
            ).exists()
        )

        unregister_response = self.client.post(
            reverse("notifications:notification-unregister-device"),
            {"fcm_token": "fcm-token-123"},
            format="json",
        )
        self.assert_success_envelope(unregister_response)
        self.assertFalse(
            UserSession.objects.filter(
                user=self.user, fcm_token="fcm-token-123"
            ).exists()
        )

    def test_user_can_get_and_update_notification_preferences(self):
        get_response = self.client.get(
            reverse("notifications:notification-preferences")
        )
        self.assert_success_envelope(get_response)
        self.assertTrue(get_response.data["data"]["push_enabled"])
        self.assertFalse(get_response.data["data"]["marketing_enabled"])

        patch_response = self.client.patch(
            reverse("notifications:notification-preferences"),
            {
                "push_enabled": False,
                "quiet_hours_enabled": True,
                "quiet_hours_start": "22:00",
                "quiet_hours_end": "06:30",
                "timezone": "Asia/Bangkok",
            },
            format="json",
        )

        self.assert_success_envelope(patch_response)
        data = patch_response.data["data"]
        self.assertFalse(data["push_enabled"])
        self.assertTrue(data["quiet_hours_enabled"])
        self.assertEqual(data["quiet_hours_start"], "22:00:00")
        self.assertEqual(data["quiet_hours_end"], "06:30:00")

    def test_invalid_notification_preference_timezone_is_rejected(self):
        response = self.client.patch(
            reverse("notifications:notification-preferences"),
            {"timezone": "Invalid/Timezone"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_notification_preference_quiet_hours_cross_midnight(self):
        preference = NotificationPreference.objects.create(
            user=self.user,
            quiet_hours_enabled=True,
            quiet_hours_start=time(22, 0),
            quiet_hours_end=time(6, 0),
            timezone="UTC",
        )

        quiet_now = datetime(2026, 6, 4, 23, 30, tzinfo=datetime_timezone.utc)
        active_now = datetime(2026, 6, 4, 12, 0, tzinfo=datetime_timezone.utc)

        self.assertFalse(
            preference.allows_push(
                category=Notification.NotificationCategory.EVENT,
                now=quiet_now,
            )
        )
        self.assertTrue(
            preference.allows_push(
                category=Notification.NotificationCategory.EVENT,
                now=active_now,
            )
        )

    def test_push_delivery_marks_sent_and_invalidates_bad_token(self):
        queued = NotificationRecipient.objects.create(
            notification=Notification.objects.create(
                title="Thông báo FCM",
                message="Kiểm thử gửi push.",
                status=Notification.NotificationStatus.SENT,
                sent_at=timezone.now(),
            ),
            user=self.user,
            delivery_status=NotificationRecipient.DeliveryStatus.QUEUED,
        )
        UserSession.objects.create(
            user=self.user,
            refresh_token_hash="fcm-session-ok",
            fcm_token="fcm-token-ok",
            expires_at=timezone.now() + timedelta(days=1),
        )

        fcm_client = FakeFcmClient()
        result = PushDeliveryService(fcm_client=fcm_client).deliver_notification(
            str(queued.notification_id)
        )

        queued.refresh_from_db()
        self.assertEqual(result["sent"], 1)
        self.assertEqual(fcm_client.messages[0]["data"]["recipient_id"], str(queued.id))
        self.assertEqual(
            fcm_client.messages[0]["data"]["notification_id"],
            str(queued.notification_id),
        )
        self.assertEqual(
            queued.delivery_status, NotificationRecipient.DeliveryStatus.SENT
        )
        self.assertIsNotNone(queued.delivered_at)

        queued.delivery_status = NotificationRecipient.DeliveryStatus.QUEUED
        queued.delivered_at = None
        queued.save(update_fields=["delivery_status", "delivered_at", "updated_at"])
        result = PushDeliveryService(
            fcm_client=FakeFcmClient(success=False, invalid_token=True)
        ).deliver_notification(str(queued.notification_id))

        queued.refresh_from_db()
        self.assertEqual(result["failed"], 1)
        self.assertEqual(result["invalid_tokens"], 1)
        self.assertEqual(
            queued.delivery_status, NotificationRecipient.DeliveryStatus.FAILED
        )
        self.assertFalse(UserSession.objects.filter(fcm_token="fcm-token-ok").exists())

    def test_push_delivery_raises_for_retryable_fcm_failure(self):
        queued = NotificationRecipient.objects.create(
            notification=Notification.objects.create(
                title="Thông báo FCM retry",
                message="Kiểm thử retry lỗi tạm thời.",
                status=Notification.NotificationStatus.SENT,
                sent_at=timezone.now(),
            ),
            user=self.user,
            delivery_status=NotificationRecipient.DeliveryStatus.QUEUED,
        )
        UserSession.objects.create(
            user=self.user,
            refresh_token_hash="fcm-session-retry",
            fcm_token="fcm-token-retry",
            expires_at=timezone.now() + timedelta(days=1),
        )

        with self.assertRaises(RetryableFcmDeliveryError):
            PushDeliveryService(
                fcm_client=FakeFcmClient(success=False, retryable=True)
            ).deliver_notification(str(queued.notification_id))

        queued.refresh_from_db()
        self.assertEqual(
            queued.delivery_status, NotificationRecipient.DeliveryStatus.QUEUED
        )
        self.assertIsNone(queued.delivered_at)
        self.assertTrue(
            UserSession.objects.filter(fcm_token="fcm-token-retry").exists()
        )

    def test_organizer_can_send_event_notification_to_audience(self):
        category = EventCategory.objects.create(name="Workshop", slug="workshop")
        event = Event.objects.create(
            category=category,
            created_by=self.user,
            title="Workshop",
            slug="workshop",
            status=Event.Status.APPROVED,
            start_at=timezone.now() + timedelta(days=1),
            end_at=timezone.now() + timedelta(days=1, hours=2),
        )
        EventOrganizer.objects.create(
            event=event,
            user=self.user,
            organizer_role=EventOrganizer.OrganizerRole.OWNER,
        )
        event.registrations.create(
            user=self.other_user,
            status="registered",
            form_answers_jsonb=[],
        )

        response = self.client.post(
            reverse(
                "notifications:organizer-event-notification-send",
                kwargs={"event_id": event.id},
            ),
            {
                "title": "Đổi phòng sự kiện",
                "message": "Sự kiện chuyển sang phòng B201.",
                "audience": "registered",
                "send_push": False,
            },
            format="json",
        )

        self.assert_success_envelope(response)
        self.assertEqual(response.data["data"]["recipient_count"], 1)
        notification = Notification.objects.get(
            id=response.data["data"]["notification_id"]
        )
        self.assertEqual(
            notification.type, Notification.NotificationType.ORGANIZER_ANNOUNCEMENT
        )
        self.assertEqual(
            notification.target, Notification.NotificationTarget.EVENT_USER
        )

    def test_organizer_notification_respects_push_preferences(self):
        category = EventCategory.objects.create(name="Seminar", slug="seminar")
        event = Event.objects.create(
            category=category,
            created_by=self.user,
            title="Seminar",
            slug="seminar",
            status=Event.Status.APPROVED,
            start_at=timezone.now() + timedelta(days=1),
            end_at=timezone.now() + timedelta(days=1, hours=2),
        )
        EventOrganizer.objects.create(
            event=event,
            user=self.user,
            organizer_role=EventOrganizer.OrganizerRole.OWNER,
        )
        event.registrations.create(
            user=self.other_user,
            status="registered",
            form_answers_jsonb=[],
        )
        NotificationPreference.objects.create(user=self.other_user, push_enabled=False)

        response = self.client.post(
            reverse(
                "notifications:organizer-event-notification-send",
                kwargs={"event_id": event.id},
            ),
            {
                "title": "Cập nhật sự kiện",
                "message": "Sự kiện có thông tin mới.",
                "audience": "registered",
                "send_push": True,
            },
            format="json",
        )

        self.assert_success_envelope(response)
        self.assertEqual(response.data["data"]["recipient_count"], 1)
        self.assertEqual(response.data["data"]["queued_count"], 0)
        recipient = NotificationRecipient.objects.get(
            notification_id=response.data["data"]["notification_id"],
            user=self.other_user,
        )
        self.assertEqual(
            recipient.delivery_status, NotificationRecipient.DeliveryStatus.SENT
        )
        self.assertIsNotNone(recipient.delivered_at)

    @override_settings(
        ORGANIZER_NOTIFICATION_RATE_LIMIT=1,
        ORGANIZER_NOTIFICATION_RATE_WINDOW_SECONDS=60,
    )
    def test_organizer_event_notification_is_rate_limited_by_actor_and_event(self):
        category = EventCategory.objects.create(name="Training", slug="training")
        event = Event.objects.create(
            category=category,
            created_by=self.user,
            title="Training",
            slug="training",
            status=Event.Status.APPROVED,
            start_at=timezone.now() + timedelta(days=1),
            end_at=timezone.now() + timedelta(days=1, hours=2),
        )
        EventOrganizer.objects.create(
            event=event,
            user=self.user,
            organizer_role=EventOrganizer.OrganizerRole.OWNER,
        )
        event.registrations.create(
            user=self.other_user,
            status="registered",
            form_answers_jsonb=[],
        )
        url = reverse(
            "notifications:organizer-event-notification-send",
            kwargs={"event_id": event.id},
        )
        payload = {
            "title": "Cập nhật sự kiện",
            "message": "Sự kiện có thông tin mới.",
            "audience": "registered",
            "send_push": False,
        }

        first_response = self.client.post(url, payload, format="json")
        second_response = self.client.post(url, payload, format="json")

        self.assert_success_envelope(first_response)
        self.assertEqual(second_response.status_code, 400)

    def test_non_organizer_cannot_send_event_notification(self):
        category = EventCategory.objects.create(name="Meetup", slug="meetup")
        event = Event.objects.create(
            category=category,
            created_by=self.other_user,
            title="Meetup",
            slug="meetup",
            status=Event.Status.APPROVED,
            start_at=timezone.now() + timedelta(days=1),
            end_at=timezone.now() + timedelta(days=1, hours=2),
        )

        response = self.client.post(
            reverse(
                "notifications:organizer-event-notification-send",
                kwargs={"event_id": event.id},
            ),
            {
                "title": "Tin mới",
                "message": "Nội dung",
                "audience": "registered",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403)
