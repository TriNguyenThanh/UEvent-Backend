from __future__ import annotations

import logging

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone

from apps.notifications.models import Notification, NotificationRecipient
from apps.notifications.services.preference_service import NotificationPreferenceService

logger = logging.getLogger(__name__)


class SystemNotificationService:
    @staticmethod
    def _greeting_for(user) -> str:
        display_name = (
            (getattr(user, "full_name", "") or "")
            or user.get_full_name()
            or getattr(user, "username", "")
            or "bạn"
        ).strip()
        return f"Xin chào {display_name},"

    @staticmethod
    def notify_event_updated(event, changes: dict, actor) -> None:
        from apps.notifications.services.event_notification_service import (
            EventNotificationService,
        )
        from apps.registrations.models import EventRegistration

        registrations = EventRegistration.objects.filter(
            event=event,
            status__in=[
                EventRegistration.RegistrationStatus.REGISTERED,
                EventRegistration.RegistrationStatus.CHECKED_IN,
            ],
        ).select_related("user")

        if not registrations.exists():
            return

        recipients = [r.user for r in registrations]

        msg_parts = []
        if "time" in changes:
            msg_parts.append("thời gian")
        if "location" in changes:
            msg_parts.append("địa điểm")
        what_changed = " và ".join(msg_parts)

        title = f"Sự kiện {event.title} có cập nhật"
        message = f"Ban tổ chức đã thay đổi {what_changed}. Vui lòng xem thông tin mới nhất."

        metadata = {
            "event_id": str(event.id),
            "role_hint": "student",
            "changes": list(changes.keys()),
        }

        EventNotificationService._create_and_dispatch(
            event=event,
            created_by=actor,
            title=title,
            message=message,
            notification_type=Notification.NotificationType.EVENT_UPDATE,
            category=Notification.NotificationCategory.EVENT,
            target=Notification.NotificationTarget.EVENT_USER,
            recipients=recipients,
            action_label="Xem sự kiện",
            metadata=metadata,
        )

        # Send emails via Celery (bulk, async)
        safe_changes: dict = {}
        if "time" in changes:
            t = changes["time"]
            safe_changes["time"] = {
                "old_start_at": t["old_start_at"].isoformat() if t.get("old_start_at") else None,
                "old_end_at": t["old_end_at"].isoformat() if t.get("old_end_at") else None,
                "new_start_at": t["new_start_at"].isoformat() if t.get("new_start_at") else None,
                "new_end_at": t["new_end_at"].isoformat() if t.get("new_end_at") else None,
            }
        if "location" in changes:
            loc = changes["location"]
            safe_changes["location"] = loc if isinstance(loc, dict) else {"old": "", "new": ""}

        user_ids = [str(u.id) for u in recipients]

        def _send_emails():
            from apps.notifications.tasks import send_event_updated_emails_task
            send_event_updated_emails_task.delay(str(event.id), user_ids, safe_changes)

        transaction.on_commit(_send_emails)

    @staticmethod
    def notify_organizer_request_approved(request) -> None:
        user = request.user
        
        # 1. Create In-App & Push Notification
        now = timezone.now()
        notification = Notification.objects.create(
            event=None,
            created_by=request.reviewed_by,
            type=Notification.NotificationType.ORGANIZER_REQUEST_APPROVED,
            category=Notification.NotificationCategory.SYSTEM,
            target=Notification.NotificationTarget.NOTIFICATION_DETAIL,
            audience_type=Notification.AudienceType.CUSTOM,
            title="Yêu cầu trở thành tổ chức đã được duyệt",
            message="Chúc mừng! Bạn đã trở thành người tổ chức sự kiện.",
            metadata={"request_id": str(request.id)},
            status=Notification.NotificationStatus.SENT,
            sent_at=now,
        )

        allows_push = NotificationPreferenceService.allows_push(
            user=user,
            category=Notification.NotificationCategory.SYSTEM,
            now=now,
        )
        NotificationRecipient.objects.create(
            notification=notification,
            user=user,
            delivery_status=(
                NotificationRecipient.DeliveryStatus.QUEUED
                if allows_push
                else NotificationRecipient.DeliveryStatus.SENT
            ),
            delivered_at=None if allows_push else now,
            failure_reason="Push disabled" if not allows_push else "",
        )

        if allows_push:
            def enqueue():
                from apps.notifications.tasks import deliver_notification
                deliver_notification.delay(str(notification.id))
            transaction.on_commit(enqueue)

        # 2. Send Email
        SystemNotificationService._send_organizer_approved_email(request)

    @staticmethod
    def _send_organizer_approved_email(request) -> None:
        user = request.user
        email = (getattr(user, "email", "") or "").strip()
        if not email:
            return

        display_name = user.get_full_name() or user.username or "bạn"
        subject = "Yêu cầu trở thành tổ chức đã được duyệt"
        message = (
            f"Xin chào {display_name},\n\n"
            "Chúc mừng! Yêu cầu trở thành người tổ chức sự kiện của bạn đã được quản trị viên duyệt.\n"
            "Bạn có thể bắt đầu tạo và quản lý sự kiện của mình ngay bây giờ trên ứng dụng UEvent.\n\n"
            "— Đội ngũ UEvent"
        )
        
        html_message = render_to_string(
            "emails/organizer_request_approved.html",
            {
                "subject": subject,
                "greeting": SystemNotificationService._greeting_for(user),
                "note": request.review_note if request.review_note else None,
                "action_url": "uevent://notifications/open?target=notification_detail",
            }
        )

        def send_email():
            try:
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    fail_silently=False,
                    html_message=html_message,
                )
            except Exception:
                logger.exception("Could not send organizer approved email to user_id=%s", user.id)

        transaction.on_commit(send_email)

    @staticmethod
    def notify_organizer_request_rejected(request) -> None:
        user = request.user
        
        # 1. Create In-App & Push Notification
        now = timezone.now()
        notification = Notification.objects.create(
            event=None,
            created_by=request.reviewed_by,
            type=Notification.NotificationType.ORGANIZER_REQUEST_REJECTED,
            category=Notification.NotificationCategory.SYSTEM,
            target=Notification.NotificationTarget.NOTIFICATION_DETAIL,
            audience_type=Notification.AudienceType.CUSTOM,
            title="Yêu cầu trở thành tổ chức đã bị từ chối",
            message=f"Rất tiếc, yêu cầu của bạn đã bị từ chối. Lý do: {request.review_note or 'Không có lý do'}",
            metadata={"request_id": str(request.id)},
            status=Notification.NotificationStatus.SENT,
            sent_at=now,
        )

        allows_push = NotificationPreferenceService.allows_push(
            user=user,
            category=Notification.NotificationCategory.SYSTEM,
            now=now,
        )
        NotificationRecipient.objects.create(
            notification=notification,
            user=user,
            delivery_status=(
                NotificationRecipient.DeliveryStatus.QUEUED
                if allows_push
                else NotificationRecipient.DeliveryStatus.SENT
            ),
            delivered_at=None if allows_push else now,
            failure_reason="Push disabled" if not allows_push else "",
        )

        if allows_push:
            def enqueue():
                from apps.notifications.tasks import deliver_notification
                deliver_notification.delay(str(notification.id))
            transaction.on_commit(enqueue)

        # 2. Send Email
        SystemNotificationService._send_organizer_rejected_email(request)

    @staticmethod
    def _send_organizer_rejected_email(request) -> None:
        user = request.user
        email = (getattr(user, "email", "") or "").strip()
        if not email:
            return

        display_name = user.get_full_name() or user.username or "bạn"
        subject = "Yêu cầu trở thành tổ chức đã bị từ chối"
        reason = request.review_note or "Không có lý do cụ thể"
        message = (
            f"Xin chào {display_name},\n\n"
            f"Rất tiếc, yêu cầu trở thành người tổ chức sự kiện của bạn đã bị quản trị viên từ chối.\n"
            f"Lý do: {reason}\n\n"
            "Bạn có thể bổ sung thông tin và gửi lại yêu cầu khác nếu cần thiết.\n\n"
            "— Đội ngũ UEvent"
        )
        
        html_message = render_to_string(
            "emails/organizer_request_rejected.html",
            {
                "subject": subject,
                "greeting": SystemNotificationService._greeting_for(user),
                "reason": reason,
                "action_url": "uevent://notifications/open?target=notification_detail",
            }
        )

        def send_email():
            try:
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    fail_silently=False,
                    html_message=html_message,
                )
            except Exception:
                logger.exception("Could not send organizer rejected email to user_id=%s", user.id)

        transaction.on_commit(send_email)

