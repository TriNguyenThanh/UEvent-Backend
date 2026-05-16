from __future__ import annotations

from django.core.cache import cache
from django.db.models import Count
from django.db.models.functions import TruncMonth
from django.utils import timezone

from apps.events.models import Event
from apps.moderation.models import ModerationLog
from apps.notifications.models import Notification
from apps.registrations.models import EventRegistration
from apps.support.models import SupportTicket
from apps.users.models import User

from .audit_log_services import AdminAuditLogService


class AdminDashboardService:
    CACHE_TIMEOUT_SECONDS = 30

    @classmethod
    def get_overview(cls) -> dict:
        return cls._cached("admin_dashboard_overview", cls._build_overview)

    @classmethod
    def get_stats(cls) -> list[dict]:
        return cls._cached("admin_dashboard_stats", cls._build_stats)

    @classmethod
    def get_growth_series(cls) -> list[dict]:
        return cls._cached("admin_dashboard_growth", cls._build_growth_series)

    @classmethod
    def get_queue(cls) -> list[dict]:
        return cls._cached("admin_dashboard_queue", cls._build_queue)

    @classmethod
    def get_audit_summary(cls) -> dict:
        return AdminAuditLogService.get_summary()

    @classmethod
    def _build_overview(cls) -> dict:
        return {
            "stats": cls._build_stats(),
            "growth_series": cls._build_growth_series(),
            "queue": cls._build_queue(),
            "audit_summary": cls.get_audit_summary(),
        }

    @staticmethod
    def _cached(key: str, factory):
        cached = cache.get(key)
        if cached is not None:
            return cached
        value = factory()
        cache.set(key, value, AdminDashboardService.CACHE_TIMEOUT_SECONDS)
        return value

    @classmethod
    def _build_stats(cls) -> list[dict]:
        now = timezone.now()
        last_30_days = now - timezone.timedelta(days=30)
        previous_30_days = now - timezone.timedelta(days=60)

        total_users = User.objects.count()
        new_users = User.objects.filter(created_at__gte=last_30_days).count()
        previous_users = User.objects.filter(created_at__gte=previous_30_days, created_at__lt=last_30_days).count()

        total_events = Event.objects.count()
        new_events = Event.objects.filter(created_at__gte=last_30_days).count()
        previous_events = Event.objects.filter(created_at__gte=previous_30_days, created_at__lt=last_30_days).count()

        total_registrations = EventRegistration.objects.count()
        new_registrations = EventRegistration.objects.filter(created_at__gte=last_30_days).count()
        previous_registrations = EventRegistration.objects.filter(
            created_at__gte=previous_30_days,
            created_at__lt=last_30_days,
        ).count()

        open_tickets = SupportTicket.objects.filter(
            status__in=[SupportTicket.TicketStatus.OPEN, SupportTicket.TicketStatus.IN_PROGRESS]
        ).count()

        return [
            {
                "id": "users",
                "title": "Người dùng",
                "value": cls._format_number(total_users),
                "trend_label": cls._format_trend(new_users, previous_users),
            },
            {
                "id": "events",
                "title": "Sự kiện",
                "value": cls._format_number(total_events),
                "trend_label": cls._format_trend(new_events, previous_events),
            },
            {
                "id": "registrations",
                "title": "Lượt đăng ký",
                "value": cls._format_number(total_registrations),
                "trend_label": cls._format_trend(new_registrations, previous_registrations),
            },
            {
                "id": "support",
                "title": "Ticket đang mở",
                "value": cls._format_number(open_tickets),
                "trend_label": "Cần xử lý",
            },
        ]

    @staticmethod
    def _build_growth_series() -> list[dict]:
        now = timezone.now()
        start_month = (now.replace(day=1) - timezone.timedelta(days=150)).replace(day=1)
        rows = (
            Event.objects.filter(created_at__gte=start_month)
            .annotate(month_start=TruncMonth("created_at"))
            .values("month_start")
            .annotate(count=Count("id"))
            .order_by("month_start")
        )
        counts = {row["month_start"].date(): row["count"] for row in rows}
        points = []
        cursor = start_month.date()
        values = []

        for _ in range(6):
            values.append(counts.get(cursor, 0))
            points.append({"date": cursor, "count": counts.get(cursor, 0)})
            next_month = (cursor.replace(day=28) + timezone.timedelta(days=4)).replace(day=1)
            cursor = next_month

        max_value = max(values) or 1
        cumulative = 0
        cumulative_values = []
        for value in values:
            cumulative += value
            cumulative_values.append(cumulative)
        max_cumulative = max(cumulative_values) or 1

        return [
            {
                "id": point["date"].strftime("%Y-%m"),
                "month": f"Th{point['date'].month}",
                "monthly_value": max(8, round(point["count"] / max_value * 100)) if point["count"] else 8,
                "yearly_value": max(8, round(cumulative_values[index] / max_cumulative * 100)),
                "highlight": index == len(points) - 1,
            }
            for index, point in enumerate(points)
        ]

    @staticmethod
    def _build_queue() -> list[dict]:
        pending_events = Event.objects.filter(status=Event.Status.PENDING).count()
        reported_events = (
            Event.objects.filter(moderation_logs__report_type__isnull=False)
            .exclude(moderation_logs__report_type="")
            .exclude(moderation_logs__report_type="manual_review")
            .distinct()
            .count()
        )
        open_tickets = SupportTicket.objects.filter(status=SupportTicket.TicketStatus.OPEN).count()
        scheduled_notifications = Notification.objects.filter(
            status=Notification.NotificationStatus.SCHEDULED,
            scheduled_at__lte=timezone.now() + timezone.timedelta(hours=24),
        ).count()
        latest_moderation = ModerationLog.objects.select_related("event").first()

        queue = [
            {
                "id": "pending-events",
                "title": "Sự kiện chờ duyệt",
                "subtitle": f"{pending_events} sự kiện cần kiểm duyệt.",
                "status": "pending" if pending_events else "completed",
                "href": "/events",
            },
            {
                "id": "reported-events",
                "title": "Sự kiện bị báo cáo",
                "subtitle": f"{reported_events} sự kiện có báo cáo từ người dùng.",
                "status": "pending" if reported_events else "completed",
                "href": "/events",
            },
            {
                "id": "open-support",
                "title": "Ticket hỗ trợ mới",
                "subtitle": f"{open_tickets} ticket đang chờ phản hồi.",
                "status": "pending" if open_tickets else "completed",
                "href": "/support",
            },
            {
                "id": "scheduled-notifications",
                "title": "Thông báo sắp gửi",
                "subtitle": f"{scheduled_notifications} thông báo sẽ đến hạn trong 24 giờ.",
                "status": "pending" if scheduled_notifications else "completed",
                "href": "/notifications",
            },
        ]

        if latest_moderation:
            queue.append(
                {
                    "id": "latest-moderation",
                    "title": latest_moderation.event.title,
                    "subtitle": f"Hoạt động kiểm duyệt gần nhất: {latest_moderation.action}.",
                    "status": "completed",
                    "href": f"/events/{latest_moderation.event_id}",
                }
            )

        return queue

    @staticmethod
    def _format_number(value: int) -> str:
        return f"{value:,}".replace(",", ".")

    @staticmethod
    def _format_trend(current: int, previous: int) -> str:
        if previous == 0:
            return "+100%" if current > 0 else "0%"
        diff = round(((current - previous) / previous) * 100)
        prefix = "+" if diff > 0 else ""
        return f"{prefix}{diff}%"
