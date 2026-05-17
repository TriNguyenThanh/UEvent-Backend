from celery import shared_task
from django.conf import settings

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
