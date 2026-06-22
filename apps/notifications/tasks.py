from celery import shared_task
from django.conf import settings

from apps.notifications.action_urls import build_event_action_url
from apps.notifications.services.push_delivery_service import PushDeliveryService


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=getattr(settings, "FCM_MAX_RETRIES", 3),
)
def deliver_notification(self, notification_id: str) -> dict:
    return PushDeliveryService().deliver_notification(notification_id)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
)
def notify_event_updated_task(self, event_id: str, actor_id: str, changes: dict) -> None:
    """
    Celery task to send in-app + push notifications and emails
    to all registered attendees when an event's time or location changes.
    Runs with automatic retry on failure.
    """
    from dateutil.parser import isoparse

    from apps.events.models import Event
    from apps.notifications.services.system_notification_service import SystemNotificationService
    from apps.users.models import User

    event = Event.objects.get(id=event_id)
    actor = User.objects.get(id=actor_id)

    # Deserialize ISO datetime strings back to datetime objects
    deserialized_changes = dict(changes)
    if "time" in deserialized_changes:
        t = deserialized_changes["time"]
        deserialized_changes["time"] = {
            "old_start_at": isoparse(t["old_start_at"]) if t.get("old_start_at") else None,
            "old_end_at": isoparse(t["old_end_at"]) if t.get("old_end_at") else None,
            "new_start_at": isoparse(t["new_start_at"]) if t.get("new_start_at") else None,
            "new_end_at": isoparse(t["new_end_at"]) if t.get("new_end_at") else None,
        }

    SystemNotificationService.notify_event_updated(event, deserialized_changes, actor)

@shared_task
def send_event_updated_emails_task(event_id: str, user_ids: list[str], changes: dict) -> None:
    from django.core.mail import send_mail
    from django.template.loader import render_to_string
    from apps.events.models import Event
    from apps.users.models import User
    from apps.notifications.services.system_notification_service import SystemNotificationService
    
    try:
        event = Event.objects.get(id=event_id)
        users = User.objects.filter(id__in=user_ids)
    except Event.DoesNotExist:
        return
        
    for user in users:
        email = (getattr(user, "email", "") or "").strip()
        if not email:
            continue
            
        display_name = user.get_full_name() or user.username or "bạn"
        subject = f"Cập nhật thông tin sự kiện: {event.title}"
        
        msg_parts = []
        if "time" in changes:
            msg_parts.append("thời gian")
        if "location" in changes:
            msg_parts.append("địa điểm")
        what_changed = " và ".join(msg_parts)
        
        message = (
            f"Xin chào {display_name},\n\n"
            f"Ban tổ chức sự kiện '{event.title}' vừa thay đổi {what_changed}.\n"
            "Vui lòng vào ứng dụng UEvent để xem thông tin chi tiết nhất.\n\n"
            "— Đội ngũ UEvent"
        )
        
        from dateutil.parser import isoparse
        template_changes = dict(changes)
        if "time" in template_changes:
            t = template_changes["time"]
            template_changes["time"] = {
                "old_start_at": isoparse(t["old_start_at"]) if t["old_start_at"] else None,
                "old_end_at": isoparse(t["old_end_at"]) if t["old_end_at"] else None,
                "new_start_at": isoparse(t["new_start_at"]) if t["new_start_at"] else None,
                "new_end_at": isoparse(t["new_end_at"]) if t["new_end_at"] else None,
            }
            
        html_message = render_to_string(
            "emails/event_updated.html",
            {
                "subject": subject,
                "greeting": SystemNotificationService._greeting_for(user),
                "event": event,
                "changes": template_changes,
                "what_changed": what_changed,
                "action_url": build_event_action_url(event.slug),
            }
        )
        
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=True,
                html_message=html_message,
            )
        except Exception:
            pass
