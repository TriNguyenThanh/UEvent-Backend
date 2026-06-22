from __future__ import annotations

from datetime import datetime, time, timedelta
from typing import Iterable

from django.db.models import Count, Q
from django.db.models.functions import TruncDay, TruncMonth, TruncWeek
from django.utils import timezone
from django.utils.dateparse import parse_date

from apps.events.models import Event
from apps.registrations.models import CheckinLog, EventRegistration, Ticket
from apps.support.models import SupportTicket
from apps.organizer_requests.models import OrganizerRequest
from apps.users.models import User, UserRole

from .audit_service import AdminAuditService
from .csv_export_service import AdminCsvExportService
from .report_excel_export_service import AdminReportExcelExportService


class AdminReportService:
    DEFAULT_DAYS = 90
    MAX_DAYS = 370

    REPORT_EXPORT_TYPES = {
        "all",
        "overview",
        "time_series",
        "status",
        "categories",
        "faculties",
        "events",
        "support",
        "organizer_requests",
    }

    @classmethod
    def get_overview(cls, filters: dict | None = None) -> dict:
        normalized_filters = cls._normalize_filters(filters or {})
        from_dt = normalized_filters["from_datetime"]
        to_dt = normalized_filters["to_datetime"]

        users = cls._within_range(User.objects.all(), "created_at", from_dt, to_dt)
        events = cls._within_range(Event.objects.all(), "created_at", from_dt, to_dt)
        registrations = cls._within_range(EventRegistration.objects.all(), "created_at", from_dt, to_dt)
        tickets = cls._within_range(Ticket.objects.all(), "created_at", from_dt, to_dt)
        support_tickets = cls._within_range(SupportTicket.objects.all(), "created_at", from_dt, to_dt)
        organizer_requests = cls._within_range(OrganizerRequest.objects.all(), "created_at", from_dt, to_dt)
        checkins = cls._within_range(CheckinLog.objects.all(), "checked_in_at", from_dt, to_dt)

        all_registrations = EventRegistration.objects.all()
        all_tickets = Ticket.objects.all()
        checked_in_registrations = registrations.filter(
            status=EventRegistration.RegistrationStatus.CHECKED_IN
        ).count()
        active_support = support_tickets.filter(
            status__in=[
                SupportTicket.TicketStatus.OPEN,
                SupportTicket.TicketStatus.IN_PROGRESS,
            ]
        ).count()
        pending_organizer_requests = organizer_requests.filter(
            status=OrganizerRequest.Status.PENDING
        ).count()
        approved_events = events.filter(
            status__in=[Event.Status.APPROVED, Event.Status.ACTIVE, Event.Status.FINISHED]
        ).count()

        metrics = [
            cls._metric(
                "users",
                "Người dùng mới",
                users.count(),
                f"{User.objects.count()} tài khoản toàn hệ thống",
                "Tài khoản tạo trong kỳ lọc",
            ),
            cls._metric(
                "organizers",
                "Người tổ chức",
                UserRole.objects.filter(role__code="organizer", user__deleted_at__isnull=True).count(),
                f"{pending_organizer_requests} yêu cầu chờ duyệt",
                "Tổng user đang có role organizer",
            ),
            cls._metric(
                "events",
                "Sự kiện tạo mới",
                events.count(),
                f"{approved_events} sự kiện đã duyệt/đang chạy/đã kết thúc",
                "Sự kiện được tạo trong kỳ lọc",
            ),
            cls._metric(
                "registrations",
                "Lượt đăng ký",
                registrations.count(),
                f"Tỷ lệ check-in {cls._percentage(checked_in_registrations, registrations.count())}%",
                "Đăng ký phát sinh trong kỳ lọc",
            ),
            cls._metric(
                "tickets",
                "Vé phát hành",
                tickets.count(),
                f"Tỷ lệ sử dụng {cls._percentage(tickets.filter(status=Ticket.TicketStatus.USED).count(), tickets.count())}%",
                "Vé tạo trong kỳ lọc",
            ),
            cls._metric(
                "support",
                "Ticket hỗ trợ",
                support_tickets.count(),
                f"{active_support} ticket đang mở hoặc đang xử lý",
                "Yêu cầu hỗ trợ phát sinh trong kỳ lọc",
            ),
        ]

        time_series = {
            "users": cls._time_series(users, "created_at", normalized_filters),
            "events": cls._time_series(events, "created_at", normalized_filters),
            "registrations": cls._time_series(registrations, "created_at", normalized_filters),
            "tickets": cls._time_series(tickets, "created_at", normalized_filters),
            "checkins": cls._time_series(checkins, "checked_in_at", normalized_filters),
            "support": cls._time_series(support_tickets, "created_at", normalized_filters),
        }

        breakdowns = {
            "users_by_status": cls._status_breakdown(users, "account_status"),
            "events_by_status": cls._status_breakdown(events, "status"),
            "registrations_by_status": cls._status_breakdown(registrations, "status"),
            "tickets_by_status": cls._status_breakdown(tickets, "status"),
            "support_by_status": cls._status_breakdown(support_tickets, "status"),
            "support_by_priority": cls._status_breakdown(support_tickets, "priority"),
            "organizer_requests_by_status": cls._status_breakdown(organizer_requests, "status"),
        }

        category_performance = cls._category_performance(from_dt, to_dt)
        faculty_distribution = cls._faculty_distribution(from_dt, to_dt)
        top_events = cls._top_events(from_dt, to_dt)
        organizer_request_summary = cls._organizer_request_summary(organizer_requests)

        funnel = [
            {"id": "events", "label": "Sự kiện được tạo", "value": events.count()},
            {"id": "approved_events", "label": "Sự kiện hợp lệ", "value": approved_events},
            {"id": "registrations", "label": "Lượt đăng ký", "value": registrations.count()},
            {"id": "tickets", "label": "Vé phát hành", "value": tickets.count()},
            {"id": "checkins", "label": "Check-in thành công", "value": checkins.filter(result=CheckinLog.CheckinResult.SUCCESS).count()},
        ]

        return {
            "generated_at": timezone.now(),
            "filters": cls._public_filters(normalized_filters),
            "metrics": metrics,
            "time_series": time_series,
            "breakdowns": breakdowns,
            "funnel": funnel,
            "category_performance": category_performance,
            "faculty_distribution": faculty_distribution,
            "top_events": top_events,
            "organizer_request_summary": organizer_request_summary,
            "system_health": [
                cls._health_item(
                    "registration_volume",
                    "Sức hút đăng ký",
                    registrations.count(),
                    all_registrations.count(),
                ),
                cls._health_item(
                    "ticket_usage",
                    "Hiệu quả sử dụng vé",
                    all_tickets.filter(status=Ticket.TicketStatus.USED).count(),
                    all_tickets.count(),
                ),
                cls._health_item(
                    "support_load",
                    "Tải hỗ trợ đang mở",
                    active_support,
                    max(support_tickets.count(), 1),
                    reverse=True,
                ),
            ],
            "insights": cls._build_insights(
                registrations_count=registrations.count(),
                checked_in_count=checked_in_registrations,
                pending_organizer_requests=pending_organizer_requests,
                active_support=active_support,
                top_events=top_events,
            ),
        }

    @classmethod
    def build_export_response(cls, *, actor, filters: dict | None = None):
        normalized_filters = cls._normalize_filters(filters or {})
        export_format = (filters or {}).get("export_format") or (filters or {}).get("format") or "csv"
        report_type = ((filters or {}).get("report_type") or "all").strip().lower()
        if report_type not in cls.REPORT_EXPORT_TYPES:
            report_type = "all"
        if export_format not in {"csv", "xlsx"}:
            export_format = "csv"

        overview = cls.get_overview(normalized_filters)
        rows = cls._export_rows(overview, report_type)
        headers = ["section", "name", "value", "detail", "extra", "period"]
        timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
        filename = f"admin_reports_{report_type}_{timestamp}.{export_format}"

        AdminAuditService.log_action(
            action="export_admin_report",
            actor=actor,
            target_type="system_admin.Report",
            target_id=report_type,
            metadata={
                "report_type": report_type,
                "export_format": export_format,
                "filters": overview["filters"],
                "rows_count": len(rows),
            },
        )

        if export_format == "xlsx":
            return AdminReportExcelExportService.build_response(
                filename=filename,
                overview=overview,
                report_type=report_type,
            )
        return AdminCsvExportService.build_response(filename=filename, headers=headers, rows=rows)

    @classmethod
    def _normalize_filters(cls, filters: dict) -> dict:
        today = timezone.localdate()
        to_date = cls._date_value(filters.get("to_date")) or today
        from_date = cls._date_value(filters.get("from_date")) or (to_date - timedelta(days=cls.DEFAULT_DAYS - 1))
        if from_date > to_date:
            from_date, to_date = to_date, from_date
        if (to_date - from_date).days > cls.MAX_DAYS:
            from_date = to_date - timedelta(days=cls.MAX_DAYS)

        from_dt = timezone.make_aware(datetime.combine(from_date, time.min))
        to_dt = timezone.make_aware(datetime.combine(to_date, time.max))
        group_by = (filters.get("group_by") or "day").strip().lower()
        if group_by not in {"day", "week", "month"}:
            group_by = "day"

        return {
            "from_date": from_date,
            "to_date": to_date,
            "from_datetime": from_dt,
            "to_datetime": to_dt,
            "group_by": group_by,
        }

    @staticmethod
    def _date_value(value):
        if value is None:
            return None
        if hasattr(value, "date"):
            return value.date()
        return parse_date(str(value))

    @staticmethod
    def _within_range(queryset, field: str, from_dt, to_dt):
        return queryset.filter(**{f"{field}__gte": from_dt, f"{field}__lte": to_dt})

    @staticmethod
    def _public_filters(filters: dict) -> dict:
        return {
            "from_date": filters["from_date"].isoformat(),
            "to_date": filters["to_date"].isoformat(),
            "group_by": filters["group_by"],
        }

    @staticmethod
    def _metric(metric_id: str, label: str, value: int, helper: str, description: str) -> dict:
        return {
            "id": metric_id,
            "label": label,
            "value": value,
            "helper": helper,
            "description": description,
        }

    @classmethod
    def _time_series(cls, queryset, field: str, filters: dict) -> list[dict]:
        trunc = {
            "day": TruncDay,
            "week": TruncWeek,
            "month": TruncMonth,
        }[filters["group_by"]]
        rows = (
            queryset.annotate(period=trunc(field))
            .values("period")
            .annotate(count=Count("id"))
            .order_by("period")
        )
        return [
            {
                "period": row["period"].date().isoformat() if row["period"] else "",
                "count": row["count"],
            }
            for row in rows
        ]

    @classmethod
    def _status_breakdown(cls, queryset, field: str) -> list[dict]:
        total = queryset.count()
        return [
            {
                "label": row[field] or "unknown",
                "count": row["count"],
                "percentage": cls._percentage(row["count"], total),
            }
            for row in queryset.values(field).annotate(count=Count("id")).order_by(field)
        ]

    @classmethod
    def _category_performance(cls, from_dt, to_dt) -> list[dict]:
        rows = (
            Event.objects.filter(created_at__gte=from_dt, created_at__lte=to_dt)
            .values("category__name")
            .annotate(
                events_count=Count("id", distinct=True),
                registration_count=Count("registrations", distinct=True),
            )
            .order_by("-registration_count", "category__name")[:12]
        )
        return [
            {
                "label": row["category__name"] or "Chưa phân loại",
                "events_count": row["events_count"],
                "registration_count": row["registration_count"],
            }
            for row in rows
        ]

    @staticmethod
    def _faculty_distribution(from_dt, to_dt) -> list[dict]:
        rows = (
            EventRegistration.objects.filter(created_at__gte=from_dt, created_at__lte=to_dt)
            .values("user__faculty")
            .annotate(count=Count("id"))
            .order_by("-count", "user__faculty")[:12]
        )
        return [
            {
                "label": row["user__faculty"] or "Chưa cập nhật",
                "count": row["count"],
            }
            for row in rows
        ]

    @classmethod
    def _top_events(cls, from_dt, to_dt) -> list[dict]:
        rows = (
            Event.objects.filter(created_at__gte=from_dt, created_at__lte=to_dt)
            .annotate(
                registration_count=Count("registrations", distinct=True),
                checkin_count=Count(
                    "registrations",
                    filter=Q(registrations__status=EventRegistration.RegistrationStatus.CHECKED_IN),
                    distinct=True,
                ),
            )
            .values(
                "id",
                "title",
                "status",
                "category__name",
                "max_capacity",
                "registration_count",
                "checkin_count",
            )
            .order_by("-registration_count", "title")[:10]
        )
        return [
            {
                "id": row["id"],
                "title": row["title"],
                "status": row["status"],
                "category": row["category__name"] or "Chưa phân loại",
                "max_capacity": row["max_capacity"] or 0,
                "registration_count": row["registration_count"],
                "checkin_count": row["checkin_count"],
                "checkin_rate": cls._percentage(row["checkin_count"], row["registration_count"]),
                "capacity_rate": cls._percentage(row["registration_count"], row["max_capacity"] or 0),
            }
            for row in rows
        ]

    @classmethod
    def _organizer_request_summary(cls, queryset) -> dict:
        total = queryset.count()
        pending = queryset.filter(status=OrganizerRequest.Status.PENDING).count()
        approved = queryset.filter(status=OrganizerRequest.Status.APPROVED).count()
        rejected = queryset.filter(status=OrganizerRequest.Status.REJECTED).count()
        return {
            "total": total,
            "pending": pending,
            "approved": approved,
            "rejected": rejected,
            "approval_rate": cls._percentage(approved, approved + rejected),
        }

    @classmethod
    def _health_item(cls, item_id: str, label: str, value: int, total: int, reverse: bool = False) -> dict:
        percentage = cls._percentage(value, total)
        score = max(0, 100 - percentage) if reverse else percentage
        return {
            "id": item_id,
            "label": label,
            "value": value,
            "total": total,
            "score": round(score, 2),
        }

    @classmethod
    def _build_insights(
        cls,
        *,
        registrations_count: int,
        checked_in_count: int,
        pending_organizer_requests: int,
        active_support: int,
        top_events: list[dict],
    ) -> list[dict]:
        insights = [
            {
                "title": "Tỷ lệ check-in",
                "description": f"{cls._percentage(checked_in_count, registrations_count)}% lượt đăng ký đã check-in trong kỳ lọc.",
                "severity": "info",
            }
        ]
        if pending_organizer_requests:
            insights.append(
                {
                    "title": "Yêu cầu organizer đang chờ",
                    "description": f"Còn {pending_organizer_requests} yêu cầu cần admin xử lý.",
                    "severity": "warning",
                }
            )
        if active_support:
            insights.append(
                {
                    "title": "Ticket hỗ trợ đang mở",
                    "description": f"Còn {active_support} ticket hỗ trợ đang mở hoặc đang xử lý.",
                    "severity": "warning",
                }
            )
        if top_events:
            insights.append(
                {
                    "title": "Sự kiện nổi bật",
                    "description": f"{top_events[0]['title']} đang dẫn đầu với {top_events[0]['registration_count']} lượt đăng ký.",
                    "severity": "success",
                }
            )
        return insights

    @classmethod
    def _export_rows(cls, overview: dict, report_type: str) -> list[dict]:
        rows: list[dict] = []

        def add(section: str, name: str, value: object, detail: object = "", extra: object = "", period: object = ""):
            rows.append(
                {
                    "section": section,
                    "name": name,
                    "value": value,
                    "detail": detail,
                    "extra": extra,
                    "period": period,
                }
            )

        if report_type in {"all", "overview"}:
            for metric in overview["metrics"]:
                add("overview", metric["label"], metric["value"], metric["helper"], metric["description"])
            for item in overview["system_health"]:
                add("system_health", item["label"], item["score"], f"{item['value']}/{item['total']}")

        if report_type in {"all", "time_series"}:
            for series_name, points in overview["time_series"].items():
                for point in points:
                    add("time_series", series_name, point["count"], period=point["period"])

        if report_type in {"all", "status"}:
            for group_name, group_rows in overview["breakdowns"].items():
                for item in group_rows:
                    add(group_name, item["label"], item["count"], f"{item['percentage']}%")

        if report_type in {"all", "categories"}:
            for item in overview["category_performance"]:
                add("categories", item["label"], item["registration_count"], f"{item['events_count']} sự kiện")

        if report_type in {"all", "faculties"}:
            for item in overview["faculty_distribution"]:
                add("faculties", item["label"], item["count"])

        if report_type in {"all", "events"}:
            for event in overview["top_events"]:
                add(
                    "events",
                    event["title"],
                    event["registration_count"],
                    f"check-in {event['checkin_rate']}%",
                    f"sức chứa {event['capacity_rate']}%",
                )

        if report_type in {"all", "support"}:
            for item in overview["breakdowns"].get("support_by_status", []):
                add("support_status", item["label"], item["count"], f"{item['percentage']}%")
            for item in overview["breakdowns"].get("support_by_priority", []):
                add("support_priority", item["label"], item["count"], f"{item['percentage']}%")

        if report_type in {"all", "organizer_requests"}:
            summary = overview["organizer_request_summary"]
            for key in ["total", "pending", "approved", "rejected", "approval_rate"]:
                add("organizer_requests", key, summary[key])

        return rows

    @staticmethod
    def _percentage(numerator: int, denominator: int) -> float:
        if denominator == 0:
            return 0.0
        return round((numerator / denominator) * 100, 2)
