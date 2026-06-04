from __future__ import annotations

import uuid

from django.conf import settings
from django.db import transaction
from django.db.models import Prefetch, Q, QuerySet
from django.utils import timezone
from django.utils.text import slugify
from rest_framework.exceptions import PermissionDenied

from apps.events.models import Event, EventOrganizer, RegistrationFormField
from apps.registrations.models import EventRegistration
from apps.users.models import User
from common.exceptions import ForbiddenError, NotFoundError, ValidationError

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


def is_event_owner(user, event):
    if not user or not user.is_authenticated:
        return False
    if event.created_by_id == user.id:
        return True
    return event.organizers.filter(
        user=user,
        organizer_role=EventOrganizer.OrganizerRole.OWNER,
    ).exists()


def assert_event_owner(actor, event):
    if not is_event_owner(actor, event):
        raise ForbiddenError("Only event owners can manage BTC members.")


class OrganizerEventService:
    @staticmethod
    def _events_with_related() -> QuerySet[Event]:
        """Base queryset with related data for event list/detail."""
        return Event.objects.select_related(
            "category", "created_by", "room__building__campus"
        ).prefetch_related(
            Prefetch(
                "organizers", queryset=EventOrganizer.objects.select_related("user")
            ),
            Prefetch(
                "registration_fields",
                queryset=RegistrationFormField.objects.order_by("sort_order"),
            ),
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
            status=data.get("status", Event.Status.DRAFT),
            slug=slug,
            registration_open_at=data.get("registration_open_at"),
            registration_close_at=data.get("registration_close_at"),
            cancellation_deadline_at=data.get("cancellation_deadline_at"),
            start_at=data.get("start_at"),
            end_at=data.get("end_at"),
            max_capacity=data.get("max_capacity"),
            location_snapshot=data.get("location_snapshot"),
            cover_image_key=data.get("cover_image_key"),
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

    @staticmethod
    def list_organizers(actor, event_id) -> QuerySet[EventOrganizer]:
        event = OrganizerEventService.get_event(actor, event_id)
        return event.organizers.select_related("user").order_by(
            "organizer_role", "user__email"
        )

    @staticmethod
    @transaction.atomic
    def add_organizer_by_email(actor, event_id, email: str) -> EventOrganizer:
        event = OrganizerEventService.get_event(actor, event_id)
        assert_event_owner(actor, event)

        user = User.objects.filter(email__iexact=email.strip()).first()
        if user is None:
            raise ValidationError({"email": "Không tìm thấy người dùng với email này."})

        role = (
            EventOrganizer.all_objects.select_for_update()
            .filter(event=event, user=user)
            .first()
        )
        if role is None:
            role = EventOrganizer.objects.create(
                event=event,
                user=user,
                organizer_role=EventOrganizer.OrganizerRole.CO_HOST,
            )
        elif role.deleted_at is not None:
            role.deleted_at = None
            role.organizer_role = EventOrganizer.OrganizerRole.CO_HOST
            role.joined_at = timezone.now()
            role.save(
                update_fields=[
                    "deleted_at",
                    "organizer_role",
                    "joined_at",
                    "updated_at",
                ]
            )
        elif (
            role.organizer_role != EventOrganizer.OrganizerRole.OWNER
            and role.user_id != event.created_by_id
            and role.organizer_role != EventOrganizer.OrganizerRole.CO_HOST
        ):
            role.organizer_role = EventOrganizer.OrganizerRole.CO_HOST
            role.save(update_fields=["organizer_role", "updated_at"])

        return EventOrganizer.all_objects.select_related("event", "user").get(
            pk=role.pk
        )

    @staticmethod
    @transaction.atomic
    def remove_organizer_by_email(actor, event_id, email: str) -> None:
        event = OrganizerEventService.get_event(actor, event_id)
        assert_event_owner(actor, event)

        role = (
            EventOrganizer.objects.select_related("user")
            .filter(
                event=event,
                user__email__iexact=email.strip(),
            )
            .first()
        )
        if role is None:
            raise NotFoundError("Không tìm thấy BTC với email này.")

        if (
            role.organizer_role == EventOrganizer.OrganizerRole.OWNER
            or role.user_id == event.created_by_id
        ):
            raise ValidationError({"email": "Không thể xóa owner khỏi đội ngũ BTC."})

        role.delete()


class PublicEventService:
    PUBLIC_EVENT_STATUSES = {Event.Status.APPROVED, Event.Status.ACTIVE}

    @staticmethod
    def _public_events_with_related() -> QuerySet[Event]:
        return Event.objects.select_related(
            "category", "created_by", "room__building__campus"
        ).prefetch_related(
            Prefetch(
                "registration_fields",
                queryset=RegistrationFormField.objects.order_by("sort_order"),
            ),
            Prefetch(
                "organizers",
                queryset=EventOrganizer.objects.select_related("user").order_by(
                    "created_at"
                ),
            ),
        )

    @staticmethod
    def search_public_events(
        *,
        search=None,
        category=None,
        status=None,
        ordering=None,
    ) -> QuerySet[Event]:
        """Search public events visible to every role."""
        queryset = Event.objects.filter(
            visibility=Event.Visibility.PUBLIC,
            status__in=PublicEventService.PUBLIC_EVENT_STATUSES,
        )

        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(description__icontains=search)
            )
        if category:
            queryset = queryset.filter(
                Q(category__slug__iexact=category)
                | Q(category__name__icontains=category)
            )
        if status in PublicEventService.PUBLIC_EVENT_STATUSES:
            queryset = queryset.filter(status=status)

        valid_ordering = {"start_at", "created_at", "updated_at", "title"}
        if ordering and ordering.lstrip("-") in valid_ordering:
            queryset = queryset.order_by(ordering)
        else:
            queryset = queryset.order_by("start_at", "-created_at")

        return queryset.select_related("category", "created_by")

    @staticmethod
    def get_public_event(event_id) -> Event:
        """Get a single public event visible to users."""
        try:
            return PublicEventService._public_events_with_related().get(
                pk=event_id,
                visibility=Event.Visibility.PUBLIC,
                status__in=PublicEventService.PUBLIC_EVENT_STATUSES,
            )
        except Event.DoesNotExist:
            raise NotFoundError(f"Event with ID {event_id} does not exist.")

    @staticmethod
    def get_public_event_by_slug(slug: str) -> Event:
        """Get a single public event by slug for landing pages."""
        try:
            return PublicEventService._public_events_with_related().get(
                slug=slug,
                visibility=Event.Visibility.PUBLIC,
                status__in=PublicEventService.PUBLIC_EVENT_STATUSES,
            )
        except Event.DoesNotExist:
            raise NotFoundError(f"Event with slug {slug} does not exist.")

    @staticmethod
    def get_shareable_public_event(event_id) -> Event:
        """Get event for public sharing, distinguishing private from unpublished."""
        try:
            event = Event.objects.only("id", "slug", "visibility", "status").get(
                pk=event_id
            )
        except Event.DoesNotExist:
            raise NotFoundError(f"Event with ID {event_id} does not exist.")

        if event.visibility == Event.Visibility.PRIVATE:
            raise ForbiddenError(
                "Sự kiện riêng tư không hỗ trợ chia sẻ liên kết công khai."
            )

        if event.status not in PublicEventService.PUBLIC_EVENT_STATUSES:
            raise NotFoundError(f"Event with ID {event_id} does not exist.")

        return event

    @staticmethod
    def build_share_url(event: Event) -> str:
        return f"{settings.PUBLIC_WEB_BASE_URL}/events/share/{event.slug}"


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
