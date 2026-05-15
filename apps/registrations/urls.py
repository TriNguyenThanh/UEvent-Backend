from django.urls import path

from apps.registrations.views import (
    EventRegistrationDetailView,
    EventRegistrationListCreateView,
    MyEventRegistrationCancelView,
    MyRegistrationListView,
    OrganizerRegistrationCancelView,
    RegistrationListCreateView,
    RegistrationQrAPIView,
    TicketCancelView,
    TicketDetailView,
    TicketListView,
    TicketQrAPIView,
)

urlpatterns = [
    path("registrations/", RegistrationListCreateView.as_view(), name="registration-list-create"),
    path("registrations/me/", MyRegistrationListView.as_view(), name="registration-me-list"),
    path("registrations/<uuid:id>/qr/", RegistrationQrAPIView.as_view(), name="registration-qr"),
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
        "events/<uuid:event_id>/registrations/<uuid:registration_id>/",
        EventRegistrationDetailView.as_view(),
        name="event-registration-detail",
    ),
    path(
        "events/<uuid:event_id>/registrations/<uuid:registration_id>/cancel/",
        OrganizerRegistrationCancelView.as_view(),
        name="event-registration-cancel",
    ),
    path("tickets/me/", TicketListView.as_view(), name="ticket-me-list"),
    path("tickets/<uuid:ticket_id>/", TicketDetailView.as_view(), name="ticket-detail"),
    path("tickets/<uuid:ticket_id>/qr/", TicketQrAPIView.as_view(), name="ticket-qr"),
    path("tickets/<uuid:ticket_id>/cancel/", TicketCancelView.as_view(), name="ticket-cancel"),
]
