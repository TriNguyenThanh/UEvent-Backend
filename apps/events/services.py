from __future__ import annotations

import uuid

from django.db import transaction
from django.db.models import Prefetch, Q, QuerySet
from django.utils.text import slugify
from rest_framework.exceptions import PermissionDenied

from apps.events.models import Event, EventOrganizer, RegistrationFormField
from apps.registrations.models import EventRegistration
from common.exceptions import ForbiddenError, NotFoundError


ORGANIZER_EVENT_LIST_ROLES = {
    EventOrganizer.OrganizerRole.OWNER,
    EventOrganizer.OrganizerRole.CO_HOST,
    EventOrganizer.OrganizerRole.STAFF,
}


def is_event_organizer(user, event):
    """Check if user is organizer of event (creator or in organizers relation)."""
    if not user or not user.is_authenticated:
        return False
    if event.created_by_id == user.id:
        return True
    return event.organizers.filter(user=user).exists()


def assert_event_organizer(actor, event):
    """Raise PermissionDenied if actor is not organizer."""
    if not is_event_organizer(actor, event):
        raise PermissionDenied("You do not have organizer access to this event.")


class OrganizerEventService:
    @staticmethod
    def _events_with_related() -> QuerySet[Event]:
        """Base queryset with related data for event list/detail."""
        return (
            Event.objects
            .select_related("category", "created_by", "room__building__campus")
            .prefetch_related(
                Prefetch("organizers", queryset=EventOrganizer.objects.select_related("user")),
                Prefetch("registration_fields", queryset=RegistrationFormField.objects.order_by("sort_order")),
            )
        )

    @staticmethod
    def _build_unique_slug(title: str, requested_slug: str = "") -> str:
        """Generate unique slug for event (max 280 chars)."""
        base_slug = slugify(requested_slug or title)
        if not base_slug:
            return slugify(f"{title}-{uuid.uuid4().hex[:8]}")

        slug = base_slug[:280]
        suffix = 1
        while Event.all_objects.filter(slug=slug).exists():
            suffix += 1
            suffix_text = f"-{suffix}"
            slug = f"{base_slug[:280 - len(suffix_text)]}{suffix_text}"
        return slug

    @staticmethod
    def list_events(
        actor,
        status=None,
        category_id=None,
        visibility=None,
        search=None,
        ordering=None,
    ) -> QuerySet[Event]:
        """
        List events for organizer.

        Only returns events where actor has owner, co-host, or staff role.
        Supports filtering by status, category_id, visibility.
        Supports search on title and description (case-insensitive).
        Supports ordering: start_at, created_at, updated_at, status.
        """
        queryset = Event.objects.filter(
            organizers__user=actor,
            organizers__organizer_role__in=ORGANIZER_EVENT_LIST_ROLES,
        ).distinct()

        if status:
            queryset = queryset.filter(status=status)
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        if visibility:
            queryset = queryset.filter(visibility=visibility)

        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(description__icontains=search)
            )

        valid_ordering = {"start_at", "created_at", "updated_at", "status"}
        if ordering and ordering.lstrip("-") in valid_ordering:
            queryset = queryset.order_by(ordering)
        else:
            queryset = queryset.order_by("-created_at")

        return queryset.select_related("category", "created_by")

    @staticmethod
    def get_event(actor, event_id) -> Event:
        """Get single event with access check. Raise NotFoundError or ForbiddenError."""
        try:
            event = OrganizerEventService._events_with_related().get(pk=event_id)
        except Event.DoesNotExist:
            raise NotFoundError(f"Event with ID {event_id} does not exist.")

        if not is_event_organizer(actor, event):
            raise ForbiddenError("You do not have organizer access to this event.")

        return event

    @staticmethod
    @transaction.atomic
    def create_event(actor, data: dict) -> Event:
        """
        Create new event.

        Auto-generates unique slug, sets created_by=actor,
        status=DRAFT, and creates event role with role=OWNER.
        """
        title = data.get("title", "")
        requested_slug = data.get("slug", "")
        slug = OrganizerEventService._build_unique_slug(title, requested_slug)
        category_id = data.get("category")
        room_id = data.get("room")

        event = Event(
            category_id=category_id,
            created_by=actor,
            title=data.get("title", ""),
            description=data.get("description", ""),
            visibility=data.get("visibility", Event.Visibility.PUBLIC),
            status=Event.Status.DRAFT,
            slug=slug,
            registration_open_at=data.get("registration_open_at"),
            registration_close_at=data.get("registration_close_at"),
            cancellation_deadline_at=data.get("cancellation_deadline_at"),
            start_at=data.get("start_at"),
            end_at=data.get("end_at"),
            max_capacity=data.get("max_capacity"),
            location_snapshot=data.get("location_snapshot"),
            cover_image_url=data.get("cover_image_url"),
            deep_link=data.get("deep_link"),
        )

        if room_id:
            event.room_id = room_id

        event.save()

        EventOrganizer.objects.get_or_create(
            event=event,
            user=actor,
            defaults={"organizer_role": EventOrganizer.OrganizerRole.OWNER},
        )

        return OrganizerEventService._events_with_related().get(pk=event.pk)

    @staticmethod
    @transaction.atomic
    def update_event(actor, event_id, data: dict) -> Event:
        """
        Update event with access check.

        Slug is not writable by organizers.
        """
        event = OrganizerEventService.get_event(actor, event_id)

        data.pop("slug", None)

        missing = object()

        category_id = data.pop("category", missing)
        if category_id is not missing:
            event.category_id = category_id

        room_id = data.pop("room", missing)
        if room_id is not missing:
            event.room_id = room_id

        for field, value in data.items():
            if hasattr(event, field):
                setattr(event, field, value)

        event.save()

        return OrganizerEventService._events_with_related().get(pk=event.pk)

    @staticmethod
    @transaction.atomic
    def delete_event(actor, event_id) -> None:
        """Soft-delete event with access check."""
        event = OrganizerEventService.get_event(actor, event_id)
        event.delete()


class PublicEventService:
    @staticmethod
    def search_public_events(
        *,
        search=None,
        category=None,
        status=None,
        ordering=None,
    ) -> QuerySet[Event]:
        """Search public events visible to every role."""
        public_statuses = {Event.Status.APPROVED, Event.Status.ACTIVE}
        queryset = Event.objects.filter(
            visibility=Event.Visibility.PUBLIC,
            status__in=public_statuses,
        )

        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(description__icontains=search)
            )
        if category:
            queryset = queryset.filter(
                Q(category__slug__iexact=category) | Q(category__name__icontains=category)
            )
        if status in public_statuses:
            queryset = queryset.filter(status=status)

        valid_ordering = {"start_at", "created_at", "updated_at", "title"}
        if ordering and ordering.lstrip("-") in valid_ordering:
            queryset = queryset.order_by(ordering)
        else:
            queryset = queryset.order_by("start_at", "-created_at")

        return queryset.select_related("category", "created_by")


class UserEventService:
    @staticmethod
    def highlight_events_for_user(actor, limit: int = 2) -> list[Event]:
        """
        Return up to ``limit`` events for the user.

        Registered events are prioritized regardless of registration status.
        If there are fewer than ``limit`` registered events, fill the rest with
        events created by the user.
        """
        if limit <= 0:
            return []

        registrations = (
            EventRegistration.objects.filter(
                user=actor,
                event__deleted_at__isnull=True,
            )
            .select_related("event", "event__category", "event__created_by")
            .order_by("-registered_at", "-created_at")[:limit]
        )
        events = [registration.event for registration in registrations]

        if len(events) >= limit:
            return events

        selected_event_ids = [event.id for event in events]
        created_events = (
            Event.objects.filter(created_by=actor)
            .exclude(id__in=selected_event_ids)
            .select_related("category", "created_by")
            .order_by("-created_at")[: limit - len(events)]
        )
        events.extend(created_events)
        return events
