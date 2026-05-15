from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count, Prefetch, Q, QuerySet
from django.utils import timezone

from apps.events.models import Event
from apps.support.models import SupportMessage, SupportTicket
from common.exceptions import NotFoundError, ValidationError

from .audit_service import AdminAuditService


class AdminSupportService:
    PRIORITY_ESCALATION_ORDER = [
        SupportTicket.TicketPriority.LOW,
        SupportTicket.TicketPriority.MEDIUM,
        SupportTicket.TicketPriority.HIGH,
        SupportTicket.TicketPriority.URGENT,
    ]

    @staticmethod
    def _tickets_with_related() -> QuerySet[SupportTicket]:
        message_prefetch = Prefetch(
            "messages",
            queryset=SupportMessage.objects.select_related("author_user").order_by("created_at"),
            to_attr="prefetched_messages",
        )
        return (
            SupportTicket.objects.select_related("user", "assigned_to")
            .annotate(message_count=Count("messages", distinct=True))
            .prefetch_related(message_prefetch)
        )

    @staticmethod
    def _log_audit(*, action, actor, ticket, reason="", metadata=None):
        AdminAuditService.log_action(
            action=action,
            actor=actor,
            target_type="support.SupportTicket",
            target_id=str(ticket.pk),
            reason=reason,
            metadata=metadata,
        )

    @staticmethod
    def list_tickets(
        *,
        status: str | None = None,
        priority: str | None = None,
        category: str | None = None,
    ) -> QuerySet[SupportTicket]:
        queryset = AdminSupportService._tickets_with_related()

        if status:
            queryset = queryset.filter(status=status)

        if priority:
            queryset = queryset.filter(priority=priority)

        if category:
            queryset = queryset.filter(category=category)

        return queryset

    @staticmethod
    def get_ticket(ticket_id) -> SupportTicket:
        try:
            ticket = AdminSupportService._tickets_with_related().get(pk=ticket_id)
        except SupportTicket.DoesNotExist as exc:
            raise NotFoundError(f"Support ticket with ID {ticket_id} does not exist.") from exc

        ticket.user_ticket_count = SupportTicket.objects.filter(user=ticket.user).count()
        ticket.user_event_count = Event.objects.filter(created_by=ticket.user).count()
        return ticket

    @staticmethod
    def get_statistics() -> dict:
        today = timezone.localdate()
        tickets = SupportTicket.objects.all()
        resolved_today = tickets.filter(
            status=SupportTicket.TicketStatus.RESOLVED,
            updated_at__date=today,
        ).count()

        response_minutes = []
        for ticket in tickets.prefetch_related("messages")[:500]:
            first_staff_message = next((message for message in ticket.messages.all() if message.is_staff), None)
            if first_staff_message:
                response_minutes.append((first_staff_message.created_at - ticket.created_at).total_seconds() / 60)

        avg_response_minutes = round(sum(response_minutes) / len(response_minutes), 1) if response_minutes else 0.0

        return {
            "open_tickets": tickets.filter(status=SupportTicket.TicketStatus.OPEN).count(),
            "in_progress": tickets.filter(status=SupportTicket.TicketStatus.IN_PROGRESS).count(),
            "resolved_today": resolved_today,
            "avg_response_minutes": avg_response_minutes,
        }

    @staticmethod
    def _get_valid_assignee(user_id):
        if not user_id:
            return None

        user_model = get_user_model()
        try:
            return user_model.objects.get(Q(is_staff=True) | Q(is_superuser=True), pk=user_id)
        except user_model.DoesNotExist as exc:
            raise ValidationError("Người được gán ticket phải là nhân sự quản trị hoặc quản trị viên.") from exc

    @staticmethod
    @transaction.atomic
    def update_ticket(*, actor, ticket_id, data: dict) -> SupportTicket:
        try:
            ticket = SupportTicket.objects.select_for_update().get(pk=ticket_id)
        except SupportTicket.DoesNotExist as exc:
            raise NotFoundError(f"Support ticket with ID {ticket_id} does not exist.") from exc

        previous = {
            "status": ticket.status,
            "priority": ticket.priority,
            "assigned_to": str(ticket.assigned_to_id) if ticket.assigned_to_id else None,
        }

        if "status" in data:
            ticket.status = data["status"]

        if "priority" in data:
            ticket.priority = data["priority"]

        if "assigned_to" in data:
            ticket.assigned_to = AdminSupportService._get_valid_assignee(data["assigned_to"])

        changed_fields = [
            field
            for field in ["status", "priority", "assigned_to"]
            if field in data
        ]
        if changed_fields:
            ticket.save(update_fields=[*changed_fields, "updated_at"])
            AdminSupportService._log_audit(
                action="update_support_ticket",
                actor=actor,
                ticket=ticket,
                metadata={
                    "previous": previous,
                    "updated_fields": changed_fields,
                },
            )

        return AdminSupportService.get_ticket(ticket_id)

    @staticmethod
    @transaction.atomic
    def reply_to_ticket(*, actor, ticket_id, content: str) -> SupportTicket:
        try:
            ticket = SupportTicket.objects.select_for_update().get(pk=ticket_id)
        except SupportTicket.DoesNotExist as exc:
            raise NotFoundError(f"Support ticket with ID {ticket_id} does not exist.") from exc

        SupportMessage.objects.create(
            ticket=ticket,
            author_user=actor,
            content=content,
            is_staff=True,
        )

        previous_status = ticket.status
        if ticket.status == SupportTicket.TicketStatus.OPEN:
            ticket.status = SupportTicket.TicketStatus.IN_PROGRESS
            ticket.save(update_fields=["status", "updated_at"])
        else:
            ticket.save(update_fields=["updated_at"])

        AdminSupportService._log_audit(
            action="reply_support_ticket",
            actor=actor,
            ticket=ticket,
            metadata={
                "previous_status": previous_status,
                "new_status": ticket.status,
                "content_length": len(content),
            },
        )
        return AdminSupportService.get_ticket(ticket_id)

    @staticmethod
    @transaction.atomic
    def resolve_ticket(*, actor, ticket_id, note: str = "") -> SupportTicket:
        try:
            ticket = SupportTicket.objects.select_for_update().get(pk=ticket_id)
        except SupportTicket.DoesNotExist as exc:
            raise NotFoundError(f"Support ticket with ID {ticket_id} does not exist.") from exc

        previous_status = ticket.status
        ticket.status = SupportTicket.TicketStatus.RESOLVED
        ticket.save(update_fields=["status", "updated_at"])

        if note:
            SupportMessage.objects.create(
                ticket=ticket,
                author_user=actor,
                content=note,
                is_staff=True,
            )

        AdminSupportService._log_audit(
            action="resolve_support_ticket",
            actor=actor,
            ticket=ticket,
            reason=note,
            metadata={"previous_status": previous_status, "new_status": ticket.status},
        )
        return AdminSupportService.get_ticket(ticket_id)

    @staticmethod
    @transaction.atomic
    def escalate_ticket(*, actor, ticket_id, reason: str = "") -> SupportTicket:
        try:
            ticket = SupportTicket.objects.select_for_update().get(pk=ticket_id)
        except SupportTicket.DoesNotExist as exc:
            raise NotFoundError(f"Support ticket with ID {ticket_id} does not exist.") from exc

        previous_priority = ticket.priority
        current_index = AdminSupportService.PRIORITY_ESCALATION_ORDER.index(ticket.priority)
        next_index = min(current_index + 1, len(AdminSupportService.PRIORITY_ESCALATION_ORDER) - 1)
        ticket.priority = AdminSupportService.PRIORITY_ESCALATION_ORDER[next_index]
        if ticket.status == SupportTicket.TicketStatus.OPEN:
            ticket.status = SupportTicket.TicketStatus.IN_PROGRESS
        ticket.save(update_fields=["priority", "status", "updated_at"])

        AdminSupportService._log_audit(
            action="escalate_support_ticket",
            actor=actor,
            ticket=ticket,
            reason=reason,
            metadata={
                "previous_priority": previous_priority,
                "new_priority": ticket.priority,
                "new_status": ticket.status,
            },
        )
        return AdminSupportService.get_ticket(ticket_id)
