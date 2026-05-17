from __future__ import annotations

import hashlib

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.notifications.models import NotificationRecipient
from apps.users.models import UserSession
from common.exceptions import NotFoundError


class NotificationInboxService:
    @staticmethod
    def list_for_user(*, user):
        return (
            NotificationRecipient.objects.select_related("notification", "notification__event")
            .filter(user=user)
            .order_by("-created_at")
        )

    @staticmethod
    def unread_count(*, user) -> int:
        return NotificationRecipient.objects.filter(user=user, read_at__isnull=True).count()

    @staticmethod
    @transaction.atomic
    def mark_read(*, user, recipient_id) -> NotificationRecipient:
        try:
            recipient = NotificationRecipient.objects.select_for_update().select_related("notification").get(
                pk=recipient_id,
                user=user,
            )
        except NotificationRecipient.DoesNotExist as exc:
            raise NotFoundError("Không tìm thấy thông báo của người dùng hiện tại.") from exc

        if recipient.read_at is None:
            recipient.read_at = timezone.now()
            recipient.delivery_status = NotificationRecipient.DeliveryStatus.READ
            recipient.save(update_fields=["read_at", "delivery_status", "updated_at"])

        return recipient

    @staticmethod
    @transaction.atomic
    def register_device(*, user, fcm_token: str, device_name: str = "", user_agent: str = "", ip_address=None) -> dict:
        token = fcm_token.strip()
        now = timezone.now()
        expires_at = now + timezone.timedelta(days=int(getattr(settings, "FCM_DEVICE_TOKEN_TTL_DAYS", 365)))
        token_hash = hashlib.sha256(f"fcm:{user.pk}:{token}".encode("utf-8")).hexdigest()

        UserSession.objects.filter(fcm_token=token).exclude(user=user).update(
            fcm_token=None,
            revoked_at=now,
            updated_at=now,
        )
        session, created = UserSession.objects.update_or_create(
            refresh_token_hash=token_hash,
            defaults={
                "user": user,
                "device_name": device_name or "Thiết bị di động",
                "user_agent": user_agent or "",
                "ip_address": ip_address,
                "fcm_token": token,
                "expires_at": expires_at,
                "revoked_at": None,
            },
        )
        return {"id": session.id, "created": created}

    @staticmethod
    @transaction.atomic
    def unregister_device(*, user, fcm_token: str) -> int:
        now = timezone.now()
        return UserSession.objects.filter(user=user, fcm_token=fcm_token.strip()).update(
            fcm_token=None,
            revoked_at=now,
            updated_at=now,
        )

    @staticmethod
    def to_output(recipient: NotificationRecipient) -> dict:
        notification = recipient.notification
        event = notification.event
        return {
            "id": recipient.id,
            "notification_id": notification.id,
            "event_id": event.id if event else None,
            "title": notification.title,
            "message": notification.message,
            "type": notification.type,
            "delivery_status": recipient.delivery_status,
            "delivered_at": recipient.delivered_at,
            "read_at": recipient.read_at,
            "action_label": "Xem sự kiện" if event else None,
            "action_route": getattr(event, "deep_link", "") if event else None,
            "created_at": recipient.created_at,
        }
