from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.notifications.models import Notification, NotificationRecipient
from apps.notifications.services.fcm_client import FcmSendResult
from apps.notifications.services.push_delivery_service import PushDeliveryService
from apps.users.models import UserSession
from common.response_codes import ResponseCode


class FakeFcmClient:
    def __init__(self, *, success=True, invalid_token=False):
        self.success = success
        self.invalid_token = invalid_token

    def send_multicast(self, *, tokens, title, body, data):
        return [
            FcmSendResult(
                token=token,
                success=self.success,
                error_code="registration-token-not-registered" if self.invalid_token else "",
                error_message="Token không còn hợp lệ." if self.invalid_token else "",
                invalid_token=self.invalid_token,
            )
            for token in tokens
        ]


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
        self.assertEqual(list_response.data["data"][0]["id"], str(self.recipient.id))

        count_response = self.client.get(reverse("notifications:notification-unread-count"))
        self.assert_success_envelope(count_response)
        self.assertEqual(count_response.data["data"]["unread_count"], 1)

        read_response = self.client.post(
            reverse("notifications:notification-mark-read", kwargs={"pk": self.recipient.pk})
        )
        self.assert_success_envelope(read_response)
        self.recipient.refresh_from_db()
        self.assertEqual(self.recipient.delivery_status, NotificationRecipient.DeliveryStatus.READ)
        self.assertIsNotNone(self.recipient.read_at)

    def test_user_cannot_mark_other_user_notification_read(self):
        other_recipient = NotificationRecipient.objects.create(
            notification=self.notification,
            user=self.other_user,
            delivery_status=NotificationRecipient.DeliveryStatus.SENT,
            delivered_at=timezone.now(),
        )

        response = self.client.post(reverse("notifications:notification-mark-read", kwargs={"pk": other_recipient.pk}))

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
        self.assertTrue(UserSession.objects.filter(user=self.user, fcm_token="fcm-token-123").exists())

        unregister_response = self.client.post(
            reverse("notifications:notification-unregister-device"),
            {"fcm_token": "fcm-token-123"},
            format="json",
        )
        self.assert_success_envelope(unregister_response)
        self.assertFalse(UserSession.objects.filter(user=self.user, fcm_token="fcm-token-123").exists())

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

        result = PushDeliveryService(fcm_client=FakeFcmClient()).deliver_notification(str(queued.notification_id))

        queued.refresh_from_db()
        self.assertEqual(result["sent"], 1)
        self.assertEqual(queued.delivery_status, NotificationRecipient.DeliveryStatus.SENT)
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
        self.assertEqual(queued.delivery_status, NotificationRecipient.DeliveryStatus.FAILED)
        self.assertFalse(UserSession.objects.filter(fcm_token="fcm-token-ok").exists())
