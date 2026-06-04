from django.urls import path

from .views import (
    NotificationInboxView,
    NotificationMarkOpenedView,
    NotificationMarkReadView,
    NotificationPreferenceView,
    OrganizerEventNotificationView,
    NotificationRegisterDeviceView,
    NotificationUnreadCountView,
    NotificationUnregisterDeviceView,
)

app_name = "notifications"

urlpatterns = [
    path("notifications/", NotificationInboxView.as_view(), name="notification-list"),
    path(
        "notifications/unread-count/",
        NotificationUnreadCountView.as_view(),
        name="notification-unread-count",
    ),
    path(
        "notifications/preferences/",
        NotificationPreferenceView.as_view(),
        name="notification-preferences",
    ),
    path(
        "notifications/<uuid:pk>/read/",
        NotificationMarkReadView.as_view(),
        name="notification-mark-read",
    ),
    path(
        "notifications/<uuid:pk>/opened/",
        NotificationMarkOpenedView.as_view(),
        name="notification-mark-opened",
    ),
    path(
        "notifications/register-device/",
        NotificationRegisterDeviceView.as_view(),
        name="notification-register-device",
    ),
    path(
        "notifications/unregister-device/",
        NotificationUnregisterDeviceView.as_view(),
        name="notification-unregister-device",
    ),
    path(
        "organizer/events/<uuid:event_id>/notifications/",
        OrganizerEventNotificationView.as_view(),
        name="organizer-event-notification-send",
    ),
]
