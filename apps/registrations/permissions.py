from __future__ import annotations

from typing import Iterable

from rest_framework.permissions import BasePermission

from apps.events.models import EventOrganizer
from apps.registrations.models import EventRegistration

HOST_ROLES = {
    EventOrganizer.OrganizerRole.OWNER,
    EventOrganizer.OrganizerRole.CO_HOST,
}
CHECKIN_ROLES = {
    EventOrganizer.OrganizerRole.OWNER,
    EventOrganizer.OrganizerRole.CO_HOST,
    EventOrganizer.OrganizerRole.STAFF,
    EventOrganizer.OrganizerRole.CHECKIN,
}


def user_has_event_role(user, event_id, roles: Iterable[str]) -> bool:
    if not user or not user.is_authenticated or not event_id:
        return False
    return EventOrganizer.objects.filter(
        event_id=event_id,
        user=user,
        organizer_role__in=list(roles),
    ).exists()


class IsEventHost(BasePermission):
    message = "Host role required to manage tickets."

    def has_permission(self, request, view):  # type: ignore[override]
        if not request.user or not request.user.is_authenticated:
            return False
        if view.action == "create":
            registration_id = request.data.get("registration_id")
            if not registration_id:
                return False
            registration = (
                EventRegistration.objects.select_related("event")
                .filter(id=registration_id)
                .first()
            )
            if not registration:
                return False
            return user_has_event_role(
                request.user,
                registration.event.id,
                HOST_ROLES,
            )
        return True

    def has_object_permission(self, request, view, obj):  # type: ignore[override]
        if not request.user or not request.user.is_authenticated:
            return False
        registration = getattr(obj, "registration", None)
        event_id = (
            registration.event.id if registration else getattr(obj, "event_id", None)
        )
        return user_has_event_role(request.user, event_id, HOST_ROLES)


class IsTicketOwnerOrOrganizer(BasePermission):
    message = "You do not have access to this ticket."

    def has_object_permission(self, request, view, obj):  # type: ignore[override]
        if not request.user or not request.user.is_authenticated:
            return False
        if obj.registration.user_id == request.user.id:
            return True
        return user_has_event_role(
            request.user,
            obj.registration.event.id,
            CHECKIN_ROLES,
        )


class IsEventCheckinStaff(BasePermission):
    message = "Check-in role required."

    def has_permission(self, request, view):  # type: ignore[override]
        event_id = request.data.get("event_id")
        return user_has_event_role(request.user, event_id, CHECKIN_ROLES)


class IsEventHostForEvent(BasePermission):
    message = "Host role required."

    def has_permission(self, request, view):  # type: ignore[override]
        event_id = view.kwargs.get("event_id")
        return user_has_event_role(request.user, event_id, HOST_ROLES)
