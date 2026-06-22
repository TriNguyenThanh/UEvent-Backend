from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterable

from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone

from apps.events.models import Event, EventOrganizer
from apps.events.services import OrganizerEventService
from apps.notifications.action_urls import build_event_action_url
from apps.notifications.models import Notification, NotificationRecipient
from apps.registrations.models import EventRegistration
from common.exceptions import ValidationError

from .preference_service import NotificationPreferenceService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class NotificationDispatchResult:
    notification: Notification
    recipient_count: int
    queued_count: int


class EventNotificationService:
    @staticmethod
    def notify_registration_created(
        registration: EventRegistration,
    ) -> dict[str, NotificationDispatchResult]:
        registration = (
            EventRegistration.objects.select_related("event", "user", "ticket")
            .prefetch_related("event__organizers")
            .get(pk=registration.pk)
        )

        results: dict[str, NotificationDispatchResult] = {}
        if registration.status == EventRegistration.RegistrationStatus.REGISTERED:
            results["participant"] = (
                EventNotificationService._notify_registration_confirmed(registration)
            )
            EventNotificationService._send_registration_confirmed_email(registration)
        elif registration.status == EventRegistration.RegistrationStatus.WAITLISTED:
            results["participant"] = (
                EventNotificationService._notify_registration_waitlisted(registration)
            )
            EventNotificationService._send_registration_waitlisted_email(registration)

        organizer_result = EventNotificationService._notify_organizers_new_registration(
            registration
        )
        if organizer_result.recipient_count:
            results["organizers"] = organizer_result
        return results

    @staticmethod
    def send_organizer_broadcast(
        *,
        actor,
        event_id,
        title: str,
        message: str,
        audience: str,
        send_push: bool = True,
    ) -> NotificationDispatchResult:
        event = OrganizerEventService.get_event(actor, event_id)
        EventNotificationService._enforce_broadcast_rate_limit(
            actor=actor,
            event=event,
        )
        recipients = EventNotificationService._resolve_audience(
            event=event, audience=audience
        )
        if not recipients:
            raise ValidationError(
                {"audience": "Không có người nhận phù hợp với nhóm đã chọn."}
            )

        metadata = {
            "event_id": str(event.id),
            "role_hint": "student",
            "audience": audience,
        }
        return EventNotificationService._create_and_dispatch(
            event=event,
            created_by=actor,
            title=title,
            message=message,
            notification_type=Notification.NotificationType.ORGANIZER_ANNOUNCEMENT,
            category=Notification.NotificationCategory.EVENT,
            target=Notification.NotificationTarget.EVENT_USER,
            recipients=recipients,
            action_label="Xem sự kiện",
            metadata=metadata,
            send_push=send_push,
        )

    @staticmethod
    def notify_registration_cancelled(registration: EventRegistration) -> None:
        registration = EventRegistration.objects.select_related(
            "event", "user", "ticket"
        ).get(pk=registration.pk)
        EventNotificationService._send_registration_cancelled_email(registration)

    @staticmethod
    def _notify_registration_confirmed(
        registration: EventRegistration,
    ) -> NotificationDispatchResult:
        event = registration.event
        ticket = getattr(registration, "ticket", None)
        target = (
            Notification.NotificationTarget.TICKET
            if ticket is not None
            else Notification.NotificationTarget.EVENT_USER
        )
        metadata = {
            "event_id": str(event.id),
            "registration_id": str(registration.id),
            "ticket_id": str(ticket.id) if ticket else "",
            "role_hint": "student",
        }
        return EventNotificationService._create_and_dispatch(
            event=event,
            created_by=None,
            title="Đăng ký sự kiện thành công",
            message=f"Bạn đã đăng ký thành công sự kiện {event.title}.",
            notification_type=Notification.NotificationType.REGISTRATION_CONFIRMED,
            category=(
                Notification.NotificationCategory.TICKET
                if ticket
                else Notification.NotificationCategory.EVENT
            ),
            target=target,
            recipients=[registration.user],
            action_label="Xem vé" if ticket else "Xem sự kiện",
            metadata=metadata,
        )

    @staticmethod
    def _notify_registration_waitlisted(
        registration: EventRegistration,
    ) -> NotificationDispatchResult:
        event = registration.event
        metadata = {
            "event_id": str(event.id),
            "registration_id": str(registration.id),
            "role_hint": "student",
        }
        return EventNotificationService._create_and_dispatch(
            event=event,
            created_by=None,
            title="Bạn đã vào danh sách chờ",
            message=f"Sự kiện {event.title} đã đủ chỗ. Bạn đã được thêm vào danh sách chờ.",
            notification_type=Notification.NotificationType.REGISTRATION_WAITLISTED,
            category=Notification.NotificationCategory.EVENT,
            target=Notification.NotificationTarget.EVENT_USER,
            recipients=[registration.user],
            action_label="Xem sự kiện",
            metadata=metadata,
        )

    @staticmethod
    def _notify_organizers_new_registration(
        registration: EventRegistration,
    ) -> NotificationDispatchResult:
        event = registration.event
        recipients = EventNotificationService._event_organizer_users(event)
        recipients = [user for user in recipients if user.id != registration.user_id]
        metadata = {
            "event_id": str(event.id),
            "registration_id": str(registration.id),
            "role_hint": "organizer",
        }
        return EventNotificationService._create_and_dispatch(
            event=event,
            created_by=None,
            title="Có người đăng ký mới",
            message=f"{registration.user.get_full_name() or registration.user.username} vừa đăng ký sự kiện {event.title}.",
            notification_type=Notification.NotificationType.NEW_REGISTRATION,
            category=Notification.NotificationCategory.ORGANIZER,
            target=Notification.NotificationTarget.ORGANIZER_REGISTRATIONS,
            recipients=recipients,
            action_label="Xem người tham gia",
            metadata=metadata,
        )

    @staticmethod
    def _send_registration_confirmed_email(registration: EventRegistration) -> None:
        event = registration.event
        ticket = getattr(registration, "ticket", None)
        action_url = (
            f"{getattr(settings, 'PUBLIC_WEB_BASE_URL', 'http://localhost:3000')}/app-redirect"
            f"?target=ticket&event_id={event.id}&ticket_id={ticket.id}"
            if ticket
            else build_event_action_url(event.slug)
        )
        lines = [
            EventNotificationService._greeting_for(registration.user),
            "",
            f"Bạn đã đăng ký thành công sự kiện {event.title}.",
            "",
            f"Thời gian: {EventNotificationService._format_event_time(event)}",
            f"Địa điểm: {EventNotificationService._format_event_location(event)}",
        ]
        if ticket is not None:
            lines.extend(["", f"Mã vé của bạn: {ticket.ticket_code}"])
        lines.extend(
            [
                "",
                "Bạn có thể mở ứng dụng UEvent để xem chi tiết sự kiện và vé tham dự.",
                "",
                "— Đội ngũ UEvent",
            ]
        )
        
        start_at = timezone.localtime(event.start_at)
        end_at = timezone.localtime(event.end_at) if event.end_at else None
        
        html_message = render_to_string(
            "emails/registration_confirmed.html",
            {
                "subject": f"Đăng ký thành công: {event.title}",
                "greeting": EventNotificationService._greeting_for(registration.user),
                "event_title": event.title,
                "time_str": EventNotificationService._format_event_time(event),
                "start_time_str": start_at.strftime("%H:%M ngày %d/%m/%Y"),
                "end_time_str": end_at.strftime("%H:%M ngày %d/%m/%Y") if end_at else None,
                "location_str": EventNotificationService._format_event_location(event),
                "ticket_code": ticket.ticket_code if ticket else None,
                "action_url": action_url,
            }
        )
        
        EventNotificationService._send_user_email_on_commit(
            user=registration.user,
            subject=f"Đăng ký thành công: {event.title}",
            message="\n".join(lines),
            html_message=html_message,
        )

    @staticmethod
    def _send_registration_waitlisted_email(registration: EventRegistration) -> None:
        event = registration.event
        message = "\n".join(
            [
                EventNotificationService._greeting_for(registration.user),
                "",
                f"Sự kiện {event.title} hiện đã đủ chỗ.",
                "Đăng ký của bạn đã được ghi nhận trong danh sách chờ.",
                "",
                f"Thời gian: {EventNotificationService._format_event_time(event)}",
                f"Địa điểm: {EventNotificationService._format_event_location(event)}",
                "",
                "UEvent sẽ cập nhật cho bạn khi trạng thái đăng ký thay đổi.",
                "",
                "— Đội ngũ UEvent",
            ]
        )
        
        start_at = timezone.localtime(event.start_at)
        end_at = timezone.localtime(event.end_at) if event.end_at else None
        
        html_message = render_to_string(
            "emails/registration_waitlisted.html",
            {
                "subject": f"Đã ghi nhận đăng ký danh sách chờ: {event.title}",
                "greeting": EventNotificationService._greeting_for(registration.user),
                "event_title": event.title,
                "time_str": EventNotificationService._format_event_time(event),
                "start_time_str": start_at.strftime("%H:%M ngày %d/%m/%Y"),
                "end_time_str": end_at.strftime("%H:%M ngày %d/%m/%Y") if end_at else None,
                "location_str": EventNotificationService._format_event_location(event),
                "action_url": build_event_action_url(event.slug),
            }
        )
        
        EventNotificationService._send_user_email_on_commit(
            user=registration.user,
            subject=f"Đã ghi nhận đăng ký danh sách chờ: {event.title}",
            message=message,
            html_message=html_message,
        )

    @staticmethod
    def _send_registration_cancelled_email(registration: EventRegistration) -> None:
        event = registration.event
        lines = [
            EventNotificationService._greeting_for(registration.user),
            "",
            f"Đăng ký của bạn cho sự kiện {event.title} đã được hủy thành công.",
            "",
            f"Thời gian: {EventNotificationService._format_event_time(event)}",
            f"Địa điểm: {EventNotificationService._format_event_location(event)}",
        ]
        if registration.cancel_reason:
            lines.extend(["", f"Lý do hủy: {registration.cancel_reason}"])
        lines.extend(
            [
                "",
                "Nếu muốn tham gia lại, bạn có thể đăng ký lại khi sự kiện còn mở đăng ký và còn chỗ.",
                "",
                "— Đội ngũ UEvent",
            ]
        )
        
        start_at = timezone.localtime(event.start_at)
        end_at = timezone.localtime(event.end_at) if event.end_at else None
        
        html_message = render_to_string(
            "emails/registration_cancelled.html",
            {
                "subject": f"Đã hủy đăng ký: {event.title}",
                "greeting": EventNotificationService._greeting_for(registration.user),
                "event_title": event.title,
                "time_str": EventNotificationService._format_event_time(event),
                "start_time_str": start_at.strftime("%H:%M ngày %d/%m/%Y"),
                "end_time_str": end_at.strftime("%H:%M ngày %d/%m/%Y") if end_at else None,
                "location_str": EventNotificationService._format_event_location(event),
                "cancel_reason": registration.cancel_reason,
                "action_url": build_event_action_url(event.slug),
            }
        )
        
        EventNotificationService._send_user_email_on_commit(
            user=registration.user,
            subject=f"Đã hủy đăng ký: {event.title}",
            message="\n".join(lines),
            html_message=html_message,
        )

    @staticmethod
    def _send_user_email_on_commit(*, user, subject: str, message: str, html_message: str = None) -> None:
        email = (getattr(user, "email", "") or "").strip()
        if not email:
            return

        def send_event_email() -> None:
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
                logger.exception(
                    "Could not send event registration email to user_id=%s",
                    getattr(user, "id", None),
                )

        transaction.on_commit(send_event_email)

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
    def _format_event_time(event: Event) -> str:
        start_at = timezone.localtime(event.start_at)
        end_at = timezone.localtime(event.end_at) if event.end_at else None
        start_text = start_at.strftime("%H:%M ngày %d/%m/%Y")
        if not end_at:
            return start_text
        if start_at.date() == end_at.date():
            return f"{start_at.strftime('%H:%M')} - {end_at.strftime('%H:%M ngày %d/%m/%Y')}"
        return f"{start_text} - {end_at.strftime('%H:%M ngày %d/%m/%Y')}"

    @staticmethod
    def _format_event_location(event: Event) -> str:
        location = (getattr(event, "location_snapshot", "") or "").strip()
        if location:
            return location

        room = getattr(event, "room", None)
        room_name = (getattr(room, "name", "") or "").strip()
        room_code = (getattr(room, "code", "") or "").strip()
        if room_name and room_code:
            return f"{room_name} ({room_code})"
        if room_name:
            return room_name
        if room_code:
            return room_code
        return "Chưa cập nhật"

    @staticmethod
    def _create_and_dispatch(
        *,
        event: Event | None,
        created_by,
        title: str,
        message: str,
        notification_type: str,
        category: str,
        target: str,
        recipients: Iterable,
        action_label: str,
        metadata: dict,
        send_push: bool = True,
    ) -> NotificationDispatchResult:
        unique_recipients = list(
            {user.id: user for user in recipients if user is not None}.values()
        )
        now = timezone.now()
        notification = Notification.objects.create(
            event=event,
            created_by=created_by,
            type=notification_type,
            category=category,
            target=target,
            audience_type=Notification.AudienceType.CUSTOM,
            title=title.strip(),
            message=message.strip(),
            action_label=action_label,
            action_route=EventNotificationService._build_action_route(
                target=target, metadata=metadata
            ),
            metadata=metadata,
            status=Notification.NotificationStatus.SENT,
            sent_at=now,
        )

        recipients_to_create = []
        queued_count = 0
        for user in unique_recipients:
            allows_push = send_push and NotificationPreferenceService.allows_push(
                user=user,
                category=category,
                now=now,
            )
            if allows_push:
                queued_count += 1
            recipients_to_create.append(
                NotificationRecipient(
                    notification=notification,
                    user=user,
                    delivery_status=(
                        NotificationRecipient.DeliveryStatus.QUEUED
                        if allows_push
                        else NotificationRecipient.DeliveryStatus.SENT
                    ),
                    delivered_at=None if allows_push else now,
                    failure_reason=(
                        "Push disabled by notification preferences."
                        if send_push and not allows_push
                        else ""
                    ),
                )
            )
        NotificationRecipient.objects.bulk_create(
            recipients_to_create, ignore_conflicts=True
        )

        if queued_count:
            transaction.on_commit(
                lambda: EventNotificationService._enqueue_delivery(str(notification.id))
            )

        return NotificationDispatchResult(
            notification=notification,
            recipient_count=len(recipients_to_create),
            queued_count=queued_count,
        )

    @staticmethod
    def _enforce_broadcast_rate_limit(*, actor, event: Event) -> None:
        limit = max(
            1,
            int(getattr(settings, "ORGANIZER_NOTIFICATION_RATE_LIMIT", 5)),
        )
        window_seconds = max(
            60,
            int(getattr(settings, "ORGANIZER_NOTIFICATION_RATE_WINDOW_SECONDS", 600)),
        )
        cache_key = f"organizer_notification_rate:{actor.id}:{event.id}"
        current_count = int(cache.get(cache_key, 0) or 0)
        if current_count >= limit:
            raise ValidationError(
                {
                    "rate_limit": (
                        "Bạn đã gửi quá nhiều thông báo cho sự kiện này. "
                        "Vui lòng thử lại sau."
                    )
                }
            )

        if cache.add(cache_key, 1, timeout=window_seconds):
            return

        try:
            new_count = cache.incr(cache_key)
        except ValueError:
            cache.add(cache_key, 1, timeout=window_seconds)
            return

        if new_count > limit:
            raise ValidationError(
                {
                    "rate_limit": (
                        "Bạn đã gửi quá nhiều thông báo cho sự kiện này. "
                        "Vui lòng thử lại sau."
                    )
                }
            )

    @staticmethod
    def _resolve_audience(*, event: Event, audience: str):
        queryset = EventRegistration.objects.filter(event=event).select_related("user")
        if audience == "registered":
            queryset = queryset.filter(
                status=EventRegistration.RegistrationStatus.REGISTERED
            )
        elif audience == "checked_in":
            queryset = queryset.filter(
                status=EventRegistration.RegistrationStatus.CHECKED_IN
            )
        elif audience == "waitlisted":
            queryset = queryset.filter(
                status=EventRegistration.RegistrationStatus.WAITLISTED
            )
        elif audience == "active":
            queryset = queryset.filter(
                status__in=[
                    EventRegistration.RegistrationStatus.REGISTERED,
                    EventRegistration.RegistrationStatus.CHECKED_IN,
                ]
            )
        elif audience == "all_participants":
            queryset = queryset.exclude(
                status__in=[
                    EventRegistration.RegistrationStatus.CANCELLED,
                    EventRegistration.RegistrationStatus.REJECTED,
                ]
            )
        else:
            raise ValidationError({"audience": "Nhóm người nhận không hợp lệ."})
        return [registration.user for registration in queryset]

    @staticmethod
    def _event_organizer_users(event: Event):
        organizer_users = [
            organizer.user
            for organizer in EventOrganizer.objects.filter(event=event).select_related(
                "user"
            )
        ]
        if event.created_by_id and all(
            user.id != event.created_by_id for user in organizer_users
        ):
            organizer_users.append(event.created_by)
        return organizer_users

    @staticmethod
    def _build_action_route(*, target: str, metadata: dict) -> str:
        params = {
            "target": target,
            "event_id": metadata.get("event_id", ""),
            "registration_id": metadata.get("registration_id", ""),
            "ticket_id": metadata.get("ticket_id", ""),
            "question_id": metadata.get("question_id", ""),
        }
        query = "&".join(f"{key}={value}" for key, value in params.items() if value)
        return f"uevent://notifications/open?{query}"

    @staticmethod
    def _enqueue_delivery(notification_id: str) -> None:
        from apps.notifications.tasks import deliver_notification

        deliver_notification.delay(notification_id)
