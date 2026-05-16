from django.urls import path

from .views import (
    audit_views,
    auth_views,
    category_views,
    dashboard_views,
    event_views,
    notification_views,
    settings_views,
    support_views,
    user_views,
)

app_name = "system_admin"

urlpatterns = [
    # Auth
    path("auth/login/", auth_views.AdminLoginView.as_view(), name="admin-login"),
    path("auth/refresh/", auth_views.AdminTokenRefreshView.as_view(), name="admin-token-refresh"),
    path("auth/logout/", auth_views.AdminLogoutView.as_view(), name="admin-logout"),
    path("auth/me/", auth_views.AdminMeView.as_view(), name="admin-me"),

    # User Management
    path("users/", user_views.AdminUserListView.as_view(), name="user-list"),
    path("users/create/", user_views.AdminUserCreateView.as_view(), name="user-create"),
    path("users/export/", user_views.AdminUserExportCreateView.as_view(), name="user-export"),
    path("users/statistics/", user_views.AdminUserStatisticsView.as_view(), name="user-statistics"),
    path("users/<uuid:pk>/", user_views.AdminUserDetailUpdateDeleteView.as_view(), name="user-detail"),
    path("users/<uuid:pk>/ban/", user_views.AdminBanUserView.as_view(), name="user-ban"),
    path("users/<uuid:pk>/unban/", user_views.AdminUnbanUserView.as_view(), name="user-unban"),
    path("users/<uuid:pk>/restore/", user_views.AdminRestoreUserView.as_view(), name="user-restore"),
    path("users/<uuid:pk>/roles/", user_views.AdminAssignRoleView.as_view(), name="user-roles"),
    path("users/<uuid:pk>/roles/<str:role_code>/", user_views.AdminRemoveRoleView.as_view(), name="user-role-remove"),
    path("exports/<uuid:job_id>/", user_views.AdminExportJobDetailView.as_view(), name="export-job-detail"),

    # Category Management
    path("categories/", category_views.AdminCategoryListCreateView.as_view(), name="category-list"),
    path("categories/statistics/", category_views.AdminCategoryStatisticsView.as_view(), name="category-statistics"),
    path("categories/<uuid:pk>/", category_views.AdminCategoryDetailUpdateDeleteView.as_view(), name="category-detail"),

    # Event Management
    path("events/", event_views.AdminEventListView.as_view(), name="event-list"),
    path("events/statistics/", event_views.AdminEventStatisticsView.as_view(), name="event-statistics"),
    path("events/moderation-pulse/", event_views.AdminEventModerationPulseView.as_view(), name="event-moderation-pulse"),
    path("events/moderation-activities/", event_views.AdminEventModerationActivitiesView.as_view(), name="event-moderation-activities"),
    path("events/policy-handbook/", event_views.AdminEventPolicyHandbookView.as_view(), name="event-policy-handbook"),
    path("events/<uuid:pk>/", event_views.AdminEventDetailDeleteView.as_view(), name="event-detail"),
    path("events/<uuid:pk>/status/", event_views.AdminEventStatusView.as_view(), name="event-status"),

    # Support Tickets
    path("support/tickets/", support_views.AdminSupportTicketListView.as_view(), name="support-ticket-list"),
    path("support/tickets/statistics/", support_views.AdminSupportTicketStatisticsView.as_view(), name="support-ticket-statistics"),
    path("support/tickets/<uuid:pk>/", support_views.AdminSupportTicketDetailUpdateView.as_view(), name="support-ticket-detail"),
    path("support/tickets/<uuid:pk>/messages/", support_views.AdminSupportTicketMessagesView.as_view(), name="support-ticket-messages"),
    path("support/tickets/<uuid:pk>/resolve/", support_views.AdminSupportTicketResolveView.as_view(), name="support-ticket-resolve"),
    path("support/tickets/<uuid:pk>/escalate/", support_views.AdminSupportTicketEscalateView.as_view(), name="support-ticket-escalate"),

    # Notifications
    path("notifications/", notification_views.AdminNotificationListCreateView.as_view(), name="notification-list"),
    path("notifications/statistics/", notification_views.AdminNotificationStatisticsView.as_view(), name="notification-statistics"),
    path("notifications/pagination-config/", notification_views.AdminNotificationPaginationConfigView.as_view(), name="notification-pagination-config"),
    path("notifications/export/", notification_views.AdminNotificationExportView.as_view(), name="notification-export"),
    path("notifications/<uuid:pk>/", notification_views.AdminNotificationDetailUpdateDeleteView.as_view(), name="notification-detail"),
    path("notifications/<uuid:pk>/publish/", notification_views.AdminNotificationPublishView.as_view(), name="notification-publish"),

    # Settings
    path("settings/", settings_views.AdminSettingsView.as_view(), name="settings"),

    # Audit Logs
    path("audit-logs/", audit_views.AdminAuditLogListView.as_view(), name="audit-log-list"),
    path("audit-logs/export/", audit_views.AdminAuditLogExportView.as_view(), name="audit-log-export"),
    path("audit-logs/summary/", audit_views.AdminAuditSummaryView.as_view(), name="audit-log-summary"),

    # Dashboard
    path("dashboard/overview/", dashboard_views.AdminDashboardOverviewView.as_view(), name="dashboard-overview"),
    path("dashboard/stats/", dashboard_views.AdminDashboardStatsView.as_view(), name="dashboard-stats"),
    path("dashboard/growth/", dashboard_views.AdminDashboardGrowthView.as_view(), name="dashboard-growth"),
    path("dashboard/queues/", dashboard_views.AdminDashboardQueueView.as_view(), name="dashboard-queues"),
    path("dashboard/audit-summary/", dashboard_views.AdminDashboardAuditSummaryView.as_view(), name="dashboard-audit-summary"),
]
