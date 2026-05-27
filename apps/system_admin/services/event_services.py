from __future__ import annotations

from django.db import transaction
from django.db.models import Count, Prefetch, QuerySet
from django.utils import timezone

from apps.events.models import Event
from apps.moderation.models import ModerationLog
from common.exceptions import NotFoundError, ValidationError

from .audit_service import AdminAuditService


class AdminEventService:
    REPORT_TYPES = {"safety", "copyright", "spam", "other"}
    STATUS_ACTION_MAP = {
        Event.Status.APPROVED: ModerationLog.Action.APPROVE,
        Event.Status.REJECTED: ModerationLog.Action.REJECT,
        Event.Status.CANCELLED: ModerationLog.Action.LOCK,
        Event.Status.ARCHIVED: ModerationLog.Action.LOCK,
        Event.Status.ACTIVE: ModerationLog.Action.REOPEN,
    }

    @staticmethod
    def _events_with_related() -> QuerySet[Event]:
        moderation_prefetch = Prefetch(
            "moderation_logs",
            queryset=ModerationLog.objects.select_related("admin_user").order_by("-created_at"),
            to_attr="prefetched_moderation_logs",
        )
        return (
            Event.objects
            .select_related("category", "created_by", "room__building__campus")
            .prefetch_related(moderation_prefetch)
        )

    @staticmethod
    def _log_audit(*, action, actor, event, reason="", metadata=None):
        AdminAuditService.log_action(
            action=action,
            actor=actor,
            target_type="events.Event",
            target_id=str(event.pk),
            reason=reason,
            metadata=metadata,
        )

    @staticmethod
    def list_events(
        *,
        status: str | None = None,
        category_id: str | None = None,
        visibility: str | None = None,
        reported: str | bool | None = None,
    ) -> QuerySet[Event]:
        queryset = AdminEventService._events_with_related()
        reported_requested = status == "reported" or str(reported or "").lower() in {"1", "true", "yes"}

        if reported_requested:
            queryset = queryset.filter(moderation_logs__report_type__in=AdminEventService.REPORT_TYPES).distinct()
        elif status:
            queryset = queryset.filter(status=status)

        if category_id:
            queryset = queryset.filter(category_id=category_id)

        if visibility:
            queryset = queryset.filter(visibility=visibility)

        return queryset

    @staticmethod
    def get_event(event_id) -> Event:
        try:
            return AdminEventService._events_with_related().get(pk=event_id)
        except Event.DoesNotExist as exc:
            raise NotFoundError(f"Event with ID {event_id} does not exist.") from exc

    @staticmethod
    def get_event_statistics() -> dict:
        events = Event.objects.select_related("category")
        today = timezone.localdate()

        return {
            "total_events": events.count(),
            "pending_approval": events.filter(status=Event.Status.PENDING).count(),
            "approved_today": events.filter(
                status=Event.Status.APPROVED,
                moderation_logs__action=ModerationLog.Action.APPROVE,
                moderation_logs__created_at__date=today,
            ).distinct().count(),
            "reported_events": events.filter(
                moderation_logs__report_type__in=AdminEventService.REPORT_TYPES,
            ).distinct().count(),
            "by_status": list(
                events.values("status").annotate(count=Count("id")).order_by("status")
            ),
            "by_category": list(
                events.values("category__id", "category__name")
                .annotate(count=Count("id"))
                .order_by("-count", "category__name")[:10]
            ),
        }

    @staticmethod
    def get_moderation_pulse() -> dict:
        pending_count = Event.objects.filter(status=Event.Status.PENDING).count()
        reported_count = Event.objects.filter(
            moderation_logs__report_type__in=AdminEventService.REPORT_TYPES,
        ).distinct().count()
        queue_size = pending_count + reported_count

        resolved_logs = ModerationLog.objects.select_related("event").filter(
            action__in=[ModerationLog.Action.APPROVE, ModerationLog.Action.REJECT],
        )[:100]
        durations = [
            (log.created_at - log.event.created_at).total_seconds() / 3600
            for log in resolved_logs
            if log.event_id and log.created_at and log.event.created_at
        ]
        avg_response_hours = round(sum(durations) / len(durations), 1) if durations else 0.0
        target_progress = 100 if avg_response_hours <= 2 and queue_size <= 10 else max(0, 100 - queue_size)

        return {
            "avg_response_hours": avg_response_hours,
            "queue_size": queue_size,
            "target_label": "Target: < 2h",
            "target_progress": min(100, target_progress),
        }

    @staticmethod
    def get_moderation_activities(limit: int = 10) -> list[dict]:
        logs = (
            ModerationLog.objects
            .select_related("event", "admin_user")
            .order_by("-created_at")[:limit]
        )
        activities = []
        for log in logs:
            if log.report_type in AdminEventService.REPORT_TYPES:
                activity_type = "flagged"
                description = f"Report type: {log.report_type}"
            elif log.action == ModerationLog.Action.APPROVE:
                activity_type = "approved"
                description = f"Approved by {getattr(log.admin_user, 'username', 'admin')}"
            elif log.action == ModerationLog.Action.REJECT:
                activity_type = "declined"
                description = log.reason or "Rejected by moderation team"
            else:
                activity_type = "flagged"
                description = log.reason or log.get_action_display()

            activities.append({
                "id": log.id,
                "event_id": log.event_id,
                "title": log.event.title,
                "description": description,
                "type": activity_type,
                "created_at": log.created_at,
            })
        return activities

    @staticmethod
    def get_policy_handbook() -> dict:
        return {
            "title": "Moderator Policy Handbook",
            "description": (
                "Ensure all events meet community standards for safety, verified "
                "organizers, lawful content, and accurate location/capacity details."
            ),
            "cta_label": "Open Docs",
            "cta_href": "#",
        }

    @staticmethod
    @transaction.atomic
    def update_event_status(*, actor, event_id, status: str, reason: str = "") -> Event:
        try:
            event = Event.objects.select_for_update().get(pk=event_id)
        except Event.DoesNotExist as exc:
            raise NotFoundError(f"Event with ID {event_id} does not exist.") from exc

        action = AdminEventService.STATUS_ACTION_MAP.get(status)
        if action is None:
            raise ValidationError("Trạng thái kiểm duyệt sự kiện không hợp lệ.")

        previous_status = event.status
        event.status = status
        event.save(update_fields=["status", "updated_at"])

        ModerationLog.objects.create(
            event=event,
            admin_user=actor,
            action=action,
            reason=reason,
        )
        AdminEventService._log_audit(
            action=f"{action}_event",
            actor=actor,
            event=event,
            reason=reason,
            metadata={"previous_status": previous_status, "new_status": status},
        )
        return AdminEventService.get_event(event_id)

    @staticmethod
    @transaction.atomic
    def delete_event(*, actor, event_id, reason: str = "") -> None:
        try:
            event = Event.objects.select_for_update().get(pk=event_id)
        except Event.DoesNotExist as exc:
            raise NotFoundError(f"Event with ID {event_id} does not exist.") from exc

        ModerationLog.objects.create(
            event=event,
            admin_user=actor,
            action=ModerationLog.Action.DELETE,
            reason=reason,
        )
        event.delete()
        AdminEventService._log_audit(
            action="delete_event",
            actor=actor,
            event=event,
            reason=reason,
            metadata={"previous_status": event.status},
        )
