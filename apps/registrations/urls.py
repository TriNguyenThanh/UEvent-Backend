from django.urls import path

from apps.registrations.views import (
    EventAttendeeListView,
    EventCheckinLogListView,
    EventCheckinScanView,
    EventTicketDetailView,
    EventTicketQrAPIView,
    EventRegistrationListCreateView,
    MyEventRegistrationCancelView,
    MyRegisteredEventListView,
    OrganizerRegistrationGrantCohostView,
    TicketCancelView,
    TicketDetailView,
    TicketQrAPIView,
)

urlpatterns = [
    path(
        "events/registrations/me/",
        MyRegisteredEventListView.as_view(),
        name="registered-event-me-list",
    ),
    path(
        "events/<uuid:event_id>/registrations/",
        EventRegistrationListCreateView.as_view(),
        name="event-registration-list-create",
    ),
    path(
        "events/<uuid:event_id>/registrations/me/",
        MyEventRegistrationCancelView.as_view(),
        name="event-registration-me-cancel",
    ),
    path(
        "organizer/events/<uuid:event_id>/registrations/<uuid:registration_id>/cohost/",
        OrganizerRegistrationGrantCohostView.as_view(),
        name="organizer-registration-grant-cohost",
    ),
    path(
        "events/<uuid:event_id>/check-in/scan/",
        EventCheckinScanView.as_view(),
        name="event-checkin-scan",
    ),
    path(
        "events/<uuid:event_id>/check-ins/",
        EventCheckinLogListView.as_view(),
        name="event-checkin-list",
    ),
    path(
        "events/<uuid:event_id>/attendees/",
        EventAttendeeListView.as_view(),
        name="event-attendee-list",
    ),
    path("events/<uuid:event_id>/ticket/", EventTicketDetailView.as_view(), name="event-ticket-detail"),
    path("events/<uuid:event_id>/ticket/token/", EventTicketQrAPIView.as_view(), name="event-ticket-token"),
    path("registrations/<uuid:registration_id>/ticket/", TicketDetailView.as_view(), name="ticket-detail"),
    path("registrations/<uuid:registration_id>/ticket/token/", TicketQrAPIView.as_view(), name="ticket-token"),
    path("registrations/<uuid:registration_id>/ticket/cancel/", TicketCancelView.as_view(), name="ticket-cancel"),
]
