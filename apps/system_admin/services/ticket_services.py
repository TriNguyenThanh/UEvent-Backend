from __future__ import annotations

from typing import Any

from django.db import transaction
from django.db.models import Q, QuerySet
from django.utils import timezone
from rest_framework.exceptions import NotFound, ValidationError

from apps.events.models import Event
from apps.registrations.models import CheckinLog, EventRegistration, Ticket
from apps.registrations.services import cancel_event_registration, process_checkin_scan

from .audit_service import AdminAuditService
from .csv_export_service import AdminCsvExportService
from .excel_export_service import AdminExcelExportService


class AdminTicketService:
    """Service quản trị vé, đăng ký và check-in."""

    EXPORT_HEADERS = [
        "ticket_code",
        "ticket_status",
        "event_title",
        "user_email",
        "user_full_name",
        "registration_status",
        "issued_at",
        "used_at",
        "expires_at",
    ]
    ORDERING_FIELDS = {
        "issued_at",
        "-issued_at",
        "used_at",
        "-used_at",
        "expires_at",
        "-expires_at",
        "status",
        "-status",
        "ticket_code",
        "-ticket_code",
    }

    @classmethod
    def tickets_with_related(cls) -> QuerySet[Ticket]:
        return Ticket.objects.select_related(
            "registration",
            "registration__event",
            "registration__user",
        )

    @classmethod
    def list_tickets(
        cls,
        *,
        status: str | None = None,
        event_id: str | None = None,
        user_id: str | None = None,
        search: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        ordering: str | None = None,
    ) -> QuerySet[Ticket]:
        queryset = cls.tickets_with_related()

        if status:
            queryset = queryset.filter(status=status)
        if event_id:
            queryset = queryset.filter(registration__event_id=event_id)
        if user_id:
            queryset = queryset.filter(registration__user_id=user_id)
        if search:
            queryset = queryset.filter(
                Q(ticket_code__icontains=search)
                | Q(registration__user__username__icontains=search)
                | Q(registration__user__full_name__icontains=search)
                | Q(registration__user__email__icontains=search)
                | Q(registration__event__title__icontains=search)
            )
        if date_from:
            queryset = queryset.filter(issued_at__gte=date_from)
        if date_to:
            queryset = queryset.filter(issued_at__lte=date_to)

        if ordering in cls.ORDERING_FIELDS:
            return queryset.order_by(ordering)
        return queryset.order_by("-issued_at", "-created_at")

    @classmethod
    def get_ticket(cls, ticket_id) -> Ticket:
        try:
            return (
                cls.tickets_with_related()
                .prefetch_related("checkin_logs__scanner_user")
                .get(pk=ticket_id)
            )
        except Ticket.DoesNotExist as exc:
            raise NotFound("Không tìm thấy vé.") from exc

    @classmethod
    def get_statistics(cls) -> dict[str, Any]:
        tickets = Ticket.objects.all()
        registrations = EventRegistration.objects.all()
        today = timezone.localdate()
        total_tickets = tickets.count()
        used_tickets = tickets.filter(status=Ticket.TicketStatus.USED).count()

        return {
            "total_tickets": total_tickets,
            "valid_tickets": tickets.filter(status=Ticket.TicketStatus.VALID).count(),
            "used_tickets": used_tickets,
            "cancelled_tickets": tickets.filter(status=Ticket.TicketStatus.CANCELLED).count(),
            "expired_tickets": tickets.filter(status=Ticket.TicketStatus.EXPIRED).count(),
            "total_registrations": registrations.count(),
            "checked_in_registrations": registrations.filter(
                status=EventRegistration.RegistrationStatus.CHECKED_IN
            ).count(),
            "checkins_today": CheckinLog.objects.filter(
                result=CheckinLog.CheckinResult.SUCCESS,
                checked_in_at__date=today,
            ).count(),
            "checkin_rate": round((used_tickets / total_tickets) * 100, 2) if total_tickets else 0,
        }

    @classmethod
    @transaction.atomic
    def cancel_ticket(cls, *, actor, ticket_id, reason: str) -> Ticket:
        try:
            ticket = (
                Ticket.objects.select_for_update()
                .select_related("registration", "registration__event", "registration__user")
                .get(pk=ticket_id)
            )
        except Ticket.DoesNotExist as exc:
            raise NotFound("Không tìm thấy vé.") from exc

        if ticket.status == Ticket.TicketStatus.USED:
            raise ValidationError({"ticket": "Không thể hủy vé đã được sử dụng."})
        if ticket.status == Ticket.TicketStatus.CANCELLED:
            raise ValidationError({"ticket": "Vé đã bị hủy trước đó."})

        cancel_event_registration(registration=ticket.registration, reason=reason)
        AdminAuditService.log_action(
            action="cancel_ticket",
            actor=actor,
            target_type="registrations.Ticket",
            target_id=str(ticket.pk),
            reason=reason,
            metadata={
                "ticket_code": ticket.ticket_code,
                "event_id": str(ticket.registration.event_id),
                "registration_id": str(ticket.registration_id),
            },
        )
        return cls.get_ticket(ticket_id)

    @classmethod
    @transaction.atomic
    def restore_ticket(cls, *, actor, ticket_id, reason: str = "") -> Ticket:
        try:
            ticket = (
                Ticket.objects.select_for_update()
                .select_related("registration", "registration__event", "registration__user")
                .get(pk=ticket_id)
            )
        except Ticket.DoesNotExist as exc:
            raise NotFound("Không tìm thấy vé.") from exc

        registration = ticket.registration
        event = registration.event
        now = timezone.now()

        if ticket.status != Ticket.TicketStatus.CANCELLED:
            raise ValidationError({"ticket": "Chỉ có thể khôi phục vé đã hủy."})
        if registration.status != EventRegistration.RegistrationStatus.CANCELLED:
            raise ValidationError({"registration": "Đăng ký của vé này chưa ở trạng thái đã hủy."})
        if ticket.used_at:
            raise ValidationError({"ticket": "Không thể khôi phục vé đã được sử dụng."})
        if ticket.expires_at <= now or event.end_at <= now:
            raise ValidationError({"ticket": "Không thể khôi phục vé đã hết hạn hoặc sự kiện đã kết thúc."})
        if event.status not in {Event.Status.APPROVED, Event.Status.ACTIVE}:
            raise ValidationError({"event": "Chỉ có thể khôi phục vé của sự kiện đang khả dụng."})

        active_registration_count = EventRegistration.objects.select_for_update().filter(
            event=event,
            status__in=[
                EventRegistration.RegistrationStatus.REGISTERED,
                EventRegistration.RegistrationStatus.CHECKED_IN,
            ],
        ).count()
        if event.max_capacity and active_registration_count >= event.max_capacity:
            raise ValidationError({"event": "Sự kiện đã đủ số lượng đăng ký."})

        registration.status = EventRegistration.RegistrationStatus.REGISTERED
        registration.cancelled_at = None
        registration.cancel_reason = None
        registration.save(update_fields=["status", "cancelled_at", "cancel_reason", "updated_at"])

        ticket.status = Ticket.TicketStatus.VALID
        ticket.used_at = None
        ticket.save(update_fields=["status", "used_at", "updated_at"])

        AdminAuditService.log_action(
            action="restore_ticket",
            actor=actor,
            target_type="registrations.Ticket",
            target_id=str(ticket.pk),
            reason=reason,
            metadata={
                "ticket_code": ticket.ticket_code,
                "event_id": str(event.pk),
                "registration_id": str(registration.pk),
            },
        )
        return cls.get_ticket(ticket_id)

    @classmethod
    def process_admin_checkin(
        cls,
        *,
        actor,
        event_id,
        ticket_code: str | None = None,
        qr_payload: str | None = None,
        qr_signature: str | None = None,
        note: str | None = None,
    ) -> dict[str, Any]:
        try:
            result = process_checkin_scan(
                event_id=event_id,
                ticket_code=ticket_code,
                qr_payload=qr_payload,
                qr_signature=qr_signature,
                scanner_user=actor,
                note=note,
            )
        except Event.DoesNotExist as exc:
            raise NotFound("Không tìm thấy sự kiện.") from exc
        except Ticket.DoesNotExist as exc:
            raise ValidationError({"ticket": "Không tìm thấy vé."}) from exc

        ticket = result.get("ticket")
        log = result["log"]
        AdminAuditService.log_action(
            action="admin_ticket_checkin_scan",
            actor=actor,
            target_type="registrations.Ticket",
            target_id=str(ticket.pk) if ticket else None,
            reason=note or "",
            metadata={
                "event_id": str(event_id),
                "result": result["result"],
                "checkin_log_id": str(log.pk),
                "ticket_code": getattr(ticket, "ticket_code", ticket_code or ""),
            },
        )
        return result

    @classmethod
    def list_checkins(
        cls,
        *,
        event_id: str | None = None,
        result: str | None = None,
        search: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> QuerySet[CheckinLog]:
        queryset = CheckinLog.objects.select_related("event", "ticket", "scanner_user")

        if event_id:
            queryset = queryset.filter(event_id=event_id)
        if result:
            queryset = queryset.filter(result=result)
        if search:
            queryset = queryset.filter(
                Q(ticket__ticket_code__icontains=search)
                | Q(event__title__icontains=search)
                | Q(scanner_user__username__icontains=search)
                | Q(scanner_user__email__icontains=search)
            )
        if date_from:
            queryset = queryset.filter(checked_in_at__gte=date_from)
        if date_to:
            queryset = queryset.filter(checked_in_at__lte=date_to)
        return queryset.order_by("-checked_in_at", "-created_at")

    @classmethod
    def build_export_response(cls, *, actor, filters: dict[str, Any], export_format: str = "csv"):
        rows = [cls._ticket_to_export_row(ticket) for ticket in cls.list_tickets(**filters)[:5000]]
        AdminAuditService.log_action(
            action="export_tickets",
            actor=actor,
            target_type="registrations.Ticket",
            reason="Xuất danh sách vé từ trang quản trị.",
            metadata={"filters": filters, "format": export_format, "row_count": len(rows)},
        )

        if export_format in {"xlsx", "excel"}:
            return AdminExcelExportService.build_response(
                filename="admin_tickets.xlsx",
                headers=cls.EXPORT_HEADERS,
                rows=rows,
                sheet_name="Tickets",
            )

        return AdminCsvExportService.build_response(
            filename="admin_tickets.csv",
            headers=cls.EXPORT_HEADERS,
            rows=rows,
        )

    @classmethod
    def _ticket_to_export_row(cls, ticket: Ticket) -> dict[str, object]:
        registration = ticket.registration
        user = registration.user
        event = registration.event
        return {
            "ticket_code": ticket.ticket_code,
            "ticket_status": ticket.status,
            "event_title": event.title,
            "user_email": user.email,
            "user_full_name": user.full_name or user.username,
            "registration_status": registration.status,
            "issued_at": ticket.issued_at.isoformat() if ticket.issued_at else "",
            "used_at": ticket.used_at.isoformat() if ticket.used_at else "",
            "expires_at": ticket.expires_at.isoformat() if ticket.expires_at else "",
        }
