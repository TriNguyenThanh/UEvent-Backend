from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db import connection, transaction
from django.db.models import Count, Q, QuerySet
from django.utils import timezone

from apps.events.models import Event
from apps.notifications.models import Notification, NotificationRecipient
from common.exceptions import NotFoundError, ValidationError

from .audit_service import AdminAuditService
from .csv_export_service import AdminCsvExportService
from .excel_export_service import AdminExcelExportService


class AdminNotificationService:
    EDITABLE_STATUSES = {
        Notification.NotificationStatus.DRAFT,
        Notification.NotificationStatus.SCHEDULED,
    }

    @staticmethod
    def _notifications_with_metrics() -> QuerySet[Notification]:
        return (
            Notification.objects.select_related("created_by", "event")
            .annotate(
                recipient_count=Count("recipients", distinct=True),
                sent_count=Count(
                    "recipients",
                    filter=Q(recipients__delivery_status__in=[
                        NotificationRecipient.DeliveryStatus.SENT,
                        NotificationRecipient.DeliveryStatus.READ,
                    ]),
                    distinct=True,
                ),
                read_count=Count(
                    "recipients",
                    filter=Q(recipients__delivery_status=NotificationRecipient.DeliveryStatus.READ),
                    distinct=True,
                ),
                failed_count=Count(
                    "recipients",
                    filter=Q(recipients__delivery_status=NotificationRecipient.DeliveryStatus.FAILED),
                    distinct=True,
                ),
            )
        )

    @staticmethod
    def _attach_open_rate(notification: Notification) -> Notification:
        sent_count = getattr(notification, "sent_count", 0) or 0
        read_count = getattr(notification, "read_count", 0) or 0
        notification.open_rate = round((read_count / sent_count) * 100, 1) if sent_count else 0.0
        return notification

    @staticmethod
    def _log_audit(*, action, actor, notification, reason="", metadata=None):
        AdminAuditService.log_action(
            action=action,
            actor=actor,
            target_type="notifications.Notification",
            target_id=str(notification.pk),
            reason=reason,
            metadata=metadata,
        )

    @staticmethod
    def list_notifications(
        *,
        status: str | None = None,
        notification_type: str | None = None,
        audience_type: str | None = None,
    ) -> QuerySet[Notification]:
        queryset = AdminNotificationService._notifications_with_metrics()

        if status:
            queryset = queryset.filter(status=status)

        if notification_type:
            queryset = queryset.filter(type=notification_type)

        if audience_type:
            queryset = queryset.filter(audience_type=audience_type)

        return queryset

    @staticmethod
    def get_notification(notification_id) -> Notification:
        try:
            notification = AdminNotificationService._notifications_with_metrics().get(pk=notification_id)
        except Notification.DoesNotExist as exc:
            raise NotFoundError(f"Notification with ID {notification_id} does not exist.") from exc

        return AdminNotificationService._attach_open_rate(notification)

    @staticmethod
    def get_statistics() -> dict:
        notifications = AdminNotificationService._notifications_with_metrics()
        sent_notifications = [
            AdminNotificationService._attach_open_rate(notification)
            for notification in notifications.filter(status=Notification.NotificationStatus.SENT)
        ]
        avg_open_rate = (
            round(sum(notification.open_rate for notification in sent_notifications) / len(sent_notifications), 1)
            if sent_notifications
            else 0.0
        )
        user_model = get_user_model()

        return {
            "total_sent": Notification.objects.filter(status=Notification.NotificationStatus.SENT).count(),
            "avg_open_rate": avg_open_rate,
            "scheduled": Notification.objects.filter(status=Notification.NotificationStatus.SCHEDULED).count(),
            "active_users": user_model.objects.filter(is_active=True).count(),
        }

    @staticmethod
    def _resolve_event(event_id):
        if not event_id:
            return None

        try:
            return Event.objects.get(pk=event_id)
        except Event.DoesNotExist as exc:
            raise ValidationError("Sự kiện gắn với thông báo không tồn tại.") from exc

    @staticmethod
    @transaction.atomic
    def create_notification(*, actor, data: dict) -> Notification:
        payload = dict(data)
        recipient_user_ids = payload.pop("recipient_user_ids", [])
        payload["event"] = AdminNotificationService._resolve_event(payload.pop("event", None))
        payload["created_by"] = actor

        notification = Notification.objects.create(**payload)
        AdminNotificationService._log_audit(
            action="create_notification",
            actor=actor,
            notification=notification,
            metadata={
                "status": notification.status,
                "audience_type": notification.audience_type,
                "recipient_user_ids_count": len(recipient_user_ids),
            },
        )
        return AdminNotificationService.get_notification(notification.pk)

    @staticmethod
    @transaction.atomic
    def update_notification(*, actor, notification_id, data: dict) -> Notification:
        try:
            notification = Notification.objects.select_for_update().get(pk=notification_id)
        except Notification.DoesNotExist as exc:
            raise NotFoundError(f"Notification with ID {notification_id} does not exist.") from exc

        if notification.status not in AdminNotificationService.EDITABLE_STATUSES:
            raise ValidationError("Chỉ được sửa thông báo nháp hoặc đã lên lịch.")

        payload = dict(data)
        payload.pop("recipient_user_ids", None)
        if "event" in payload:
            payload["event"] = AdminNotificationService._resolve_event(payload.pop("event"))

        for field, value in payload.items():
            setattr(notification, field, value)

        if payload:
            notification.save(update_fields=[*payload.keys(), "updated_at"])
            AdminNotificationService._log_audit(
                action="update_notification",
                actor=actor,
                notification=notification,
                metadata={"updated_fields": list(payload.keys())},
            )

        return AdminNotificationService.get_notification(notification_id)

    @staticmethod
    def _get_audience_users(notification: Notification, recipient_user_ids: list | None = None):
        user_model = get_user_model()
        users = user_model.objects.filter(is_active=True)

        if recipient_user_ids:
            return users.filter(pk__in=recipient_user_ids)

        if notification.audience_type == Notification.AudienceType.STUDENTS:
            return users.filter(is_staff=False, is_superuser=False)

        if notification.audience_type == Notification.AudienceType.ORGANIZERS:
            return users.filter(user_roles__role__code="organizer").distinct()

        if notification.audience_type == Notification.AudienceType.ADMINS:
            return users.filter(Q(is_staff=True) | Q(is_superuser=True))

        if notification.audience_type == Notification.AudienceType.CUSTOM:
            return users.none()

        return users

    @staticmethod
    @transaction.atomic
    def publish_notification(*, actor, notification_id, recipient_user_ids: list | None = None) -> Notification:
        try:
            notification = Notification.objects.select_for_update().get(pk=notification_id)
        except Notification.DoesNotExist as exc:
            raise NotFoundError(f"Notification with ID {notification_id} does not exist.") from exc

        if notification.status == Notification.NotificationStatus.SENT:
            raise ValidationError("Thông báo này đã được gửi.")

        return AdminNotificationService._publish_locked_notification(
            actor=actor,
            notification=notification,
            recipient_user_ids=recipient_user_ids,
            audit_action="publish_notification",
        )

    @staticmethod
    def _publish_locked_notification(
        *,
        actor,
        notification: Notification,
        recipient_user_ids: list | None = None,
        audit_action: str = "publish_notification",
    ) -> Notification:
        users = list(AdminNotificationService._get_audience_users(notification, recipient_user_ids))
        now = timezone.now()
        NotificationRecipient.objects.bulk_create(
            [
                NotificationRecipient(
                    notification=notification,
                    user=user,
                    delivery_status=NotificationRecipient.DeliveryStatus.SENT,
                    delivered_at=now,
                )
                for user in users
            ],
            ignore_conflicts=True,
        )

        previous_status = notification.status
        notification.status = Notification.NotificationStatus.SENT
        notification.sent_at = now
        notification.save(update_fields=["status", "sent_at", "updated_at"])

        AdminNotificationService._log_audit(
            action=audit_action,
            actor=actor,
            notification=notification,
            metadata={
                "previous_status": previous_status,
                "recipient_count": len(users),
                "audience_type": notification.audience_type,
                "scheduled_at": notification.scheduled_at.isoformat() if notification.scheduled_at else None,
            },
        )
        return AdminNotificationService.get_notification(notification.pk)

    @staticmethod
    def publish_due_scheduled_notifications(*, actor=None, batch_size: int = 100, now=None) -> dict:
        cutoff = now or timezone.now()
        published_ids: list[str] = []

        for _ in range(max(0, batch_size)):
            with transaction.atomic():
                queryset = Notification.objects.filter(
                    status=Notification.NotificationStatus.SCHEDULED,
                    scheduled_at__isnull=False,
                    scheduled_at__lte=cutoff,
                )
                if connection.features.has_select_for_update:
                    queryset = queryset.select_for_update(
                        skip_locked=connection.features.has_select_for_update_skip_locked
                    )

                notification = queryset.order_by("scheduled_at", "created_at").first()

                if notification is None:
                    break

                published_notification = AdminNotificationService._publish_locked_notification(
                    actor=actor,
                    notification=notification,
                    audit_action="publish_scheduled_notification",
                )
                published_ids.append(str(published_notification.pk))

        remaining_due = Notification.objects.filter(
            status=Notification.NotificationStatus.SCHEDULED,
            scheduled_at__isnull=False,
            scheduled_at__lte=cutoff,
        ).count()

        return {
            "published_count": len(published_ids),
            "published_ids": published_ids,
            "remaining_due": remaining_due,
            "cutoff": cutoff,
        }

    @staticmethod
    @transaction.atomic
    def delete_notification(*, actor, notification_id) -> None:
        try:
            notification = Notification.objects.select_for_update().get(pk=notification_id)
        except Notification.DoesNotExist as exc:
            raise NotFoundError(f"Notification with ID {notification_id} does not exist.") from exc

        if notification.status not in AdminNotificationService.EDITABLE_STATUSES:
            raise ValidationError("Chỉ được xóa thông báo nháp hoặc đã lên lịch.")

        previous_status = notification.status
        notification.delete()
        AdminNotificationService._log_audit(
            action="delete_notification",
            actor=actor,
            notification=notification,
            metadata={"previous_status": previous_status},
        )

    @staticmethod
    def export_notifications(*, actor, filters: dict, export_format: str = "csv"):
        normalized_format = (export_format or "csv").lower()
        if normalized_format == "excel":
            normalized_format = "xlsx"

        if normalized_format not in {"csv", "xlsx"}:
            raise ValidationError("Định dạng xuất thông báo không hợp lệ.")

        headers = [
            "id",
            "title",
            "type",
            "audience_type",
            "status",
            "recipient_count",
            "sent_count",
            "read_count",
            "failed_count",
            "open_rate",
            "scheduled_at",
            "sent_at",
            "created_at",
        ]
        rows = []
        for notification in AdminNotificationService.list_notifications(
            status=filters.get("status"),
            notification_type=filters.get("type"),
            audience_type=filters.get("audience_type"),
        ):
            notification = AdminNotificationService._attach_open_rate(notification)
            rows.append(
                {
                    "id": notification.id,
                    "title": notification.title,
                    "type": notification.type,
                    "audience_type": notification.audience_type,
                    "status": notification.status,
                    "recipient_count": getattr(notification, "recipient_count", 0),
                    "sent_count": getattr(notification, "sent_count", 0),
                    "read_count": getattr(notification, "read_count", 0),
                    "failed_count": getattr(notification, "failed_count", 0),
                    "open_rate": notification.open_rate,
                    "scheduled_at": notification.scheduled_at,
                    "sent_at": notification.sent_at,
                    "created_at": notification.created_at,
                }
            )

        AdminAuditService.log_action(
            action="export_notifications",
            actor=actor,
            target_type="notifications.Notification",
            metadata={"filters": filters, "format": normalized_format, "rows_count": len(rows)},
        )
        if normalized_format == "xlsx":
            return AdminExcelExportService.build_response(
                filename=f"notifications-{timezone.localdate().isoformat()}.xlsx",
                headers=headers,
                rows=rows,
                sheet_name="Notifications",
            )

        return AdminCsvExportService.build_response(
            filename=f"notifications-{timezone.localdate().isoformat()}.csv",
            headers=headers,
            rows=rows,
        )
