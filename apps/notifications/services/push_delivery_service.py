from __future__ import annotations

import logging
from collections import defaultdict

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.notifications.models import Notification, NotificationRecipient
from apps.users.models import UserSession

from .fcm_client import FcmClient, FcmSendResult


logger = logging.getLogger(__name__)


class PushDeliveryService:
    def __init__(self, fcm_client: FcmClient | None = None):
        self.fcm_client = fcm_client or FcmClient()
        self.batch_size = max(1, min(500, int(getattr(settings, "FCM_BATCH_SIZE", 500))))

    def deliver_notification(self, notification_id: str) -> dict:
        notification = Notification.objects.select_related("event").get(pk=notification_id)
        recipients = list(
            NotificationRecipient.objects.select_related("user")
            .filter(notification=notification, delivery_status=NotificationRecipient.DeliveryStatus.QUEUED)
            .order_by("created_at")[: self.batch_size]
        )
        if not recipients:
            return {"notification_id": str(notification.id), "queued": 0, "sent": 0, "failed": 0, "invalid_tokens": 0}

        user_ids = [recipient.user_id for recipient in recipients]
        sessions = list(
            UserSession.objects.filter(
                user_id__in=user_ids,
                fcm_token__isnull=False,
                revoked_at__isnull=True,
                expires_at__gt=timezone.now(),
            ).exclude(fcm_token="")
        )
        tokens_by_user: dict[str, list[str]] = defaultdict(list)
        for session in sessions:
            tokens_by_user[str(session.user_id)].append(session.fcm_token)

        token_recipient_pairs: list[tuple[str, NotificationRecipient]] = []
        failed_without_token: list[NotificationRecipient] = []
        for recipient in recipients:
            tokens = tokens_by_user.get(str(recipient.user_id), [])
            if not tokens:
                failed_without_token.append(recipient)
                continue
            token_recipient_pairs.extend((token, recipient) for token in tokens)

        now = timezone.now()
        if failed_without_token:
            NotificationRecipient.objects.filter(id__in=[item.id for item in failed_without_token]).update(
                delivery_status=NotificationRecipient.DeliveryStatus.FAILED,
                delivered_at=None,
                updated_at=now,
            )

        results = self._send(notification, [token for token, _ in token_recipient_pairs])
        result_by_token = {result.token: result for result in results}
        sent_recipient_ids: set[str] = set()
        failed_recipient_ids: set[str] = set()
        invalid_tokens: list[str] = []

        for token, recipient in token_recipient_pairs:
            result = result_by_token.get(token)
            if result and result.success:
                sent_recipient_ids.add(str(recipient.id))
                continue

            failed_recipient_ids.add(str(recipient.id))
            if result and result.invalid_token:
                invalid_tokens.append(token)
                logger.warning(
                    "FCM invalid token for notification=%s recipient=%s code=%s",
                    notification.id,
                    recipient.id,
                    result.error_code,
                )
            elif result:
                logger.warning(
                    "FCM delivery failed notification=%s recipient=%s code=%s message=%s",
                    notification.id,
                    recipient.id,
                    result.error_code,
                    result.error_message,
                )

        failed_recipient_ids -= sent_recipient_ids
        self._persist_delivery_results(
            sent_recipient_ids=sent_recipient_ids,
            failed_recipient_ids=failed_recipient_ids,
            invalid_tokens=invalid_tokens,
            now=now,
        )

        return {
            "notification_id": str(notification.id),
            "queued": len(recipients),
            "sent": len(sent_recipient_ids),
            "failed": len(failed_recipient_ids) + len(failed_without_token),
            "invalid_tokens": len(set(invalid_tokens)),
        }

    def _send(self, notification: Notification, tokens: list[str]) -> list[FcmSendResult]:
        if not tokens:
            return []

        return self.fcm_client.send_multicast(
            tokens=tokens,
            title=notification.title,
            body=notification.message,
            data=self._build_payload(notification),
        )

    @staticmethod
    def _build_payload(notification: Notification) -> dict[str, str]:
        event = notification.event
        return {
            "notification_id": str(notification.id),
            "event_id": str(event.id) if event else "",
            "deep_link": getattr(event, "deep_link", "") if event else "",
            "type": notification.type,
        }

    @staticmethod
    @transaction.atomic
    def _persist_delivery_results(
        *,
        sent_recipient_ids: set[str],
        failed_recipient_ids: set[str],
        invalid_tokens: list[str],
        now,
    ) -> None:
        if sent_recipient_ids:
            NotificationRecipient.objects.filter(id__in=sent_recipient_ids).update(
                delivery_status=NotificationRecipient.DeliveryStatus.SENT,
                delivered_at=now,
                updated_at=now,
            )

        if failed_recipient_ids:
            NotificationRecipient.objects.filter(id__in=failed_recipient_ids).update(
                delivery_status=NotificationRecipient.DeliveryStatus.FAILED,
                updated_at=now,
            )

        if invalid_tokens:
            UserSession.objects.filter(fcm_token__in=set(invalid_tokens)).update(
                fcm_token=None,
                revoked_at=now,
                updated_at=now,
            )
