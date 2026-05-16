from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.events.models import Event, EventCategory, EventOrganizer, RegistrationFormField
from apps.locations.models import Building, Campus, Room
from apps.registrations.models import EventRegistration, Ticket
from apps.registrations.services import build_qr_payload, generate_ticket_code, sign_qr_payload
from apps.users.management.commands.seed_roles import DEFAULT_ROLES
from apps.users.models import Role, UserRole
from apps.utils.seed_data import (
    SEED_BUILDING_CODES,
    SEED_CAMPUS_CODES,
    SEED_CATEGORIES,
    SEED_CATEGORY_SLUGS,
    SEED_EVENTS,
    SEED_EVENT_SLUGS,
    SEED_LOCATIONS,
    SEED_PASSWORD,
    SEED_REGISTRATIONS,
    SEED_ROOM_CODES,
    SEED_USERS,
    SEED_USERNAMES,
)


class Command(BaseCommand):
    help = "Seed sample data for local development and demos."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing seeded users, events, categories, and locations before seeding.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["reset"]:
            self._reset_seed_data()

        roles = self._seed_roles()
        users = self._seed_users(roles)
        rooms = self._seed_locations()
        categories = self._seed_categories()
        events = self._seed_events(users["organizer"], categories, rooms)
        self._seed_registrations(events, users)

        self.stdout.write(
            self.style.SUCCESS(
                "Seed data ready. Login with admin/organizer/student01 using password: "
                f"{SEED_PASSWORD}"
            )
        )

    def _reset_seed_data(self):
        User = get_user_model()

        Event.objects.filter(slug__in=SEED_EVENT_SLUGS).delete()
        EventCategory.objects.filter(slug__in=SEED_CATEGORY_SLUGS).delete()
        User.objects.filter(username__in=SEED_USERNAMES).delete()
        Room.objects.filter(code__in=SEED_ROOM_CODES).delete()
        Building.objects.filter(code__in=SEED_BUILDING_CODES).delete()
        Campus.objects.filter(code__in=SEED_CAMPUS_CODES).delete()

        self.stdout.write("Reset existing seed data.")

    def _seed_roles(self):
        roles = {}
        for role_data in DEFAULT_ROLES:
            role, _ = Role.all_objects.update_or_create(
                code=role_data["code"],
                defaults={
                    "name": role_data["name"],
                    "description": role_data["description"],
                    "is_active": True,
                    "deleted_at": None,
                },
            )
            roles[role.code] = role
        return roles

    def _seed_users(self, roles):
        User = get_user_model()
        users = {}

        for user_data in SEED_USERS:
            user, _ = User.all_objects.update_or_create(
                username=user_data["username"],
                defaults={
                    "email": user_data["email"],
                    "full_name": user_data["full_name"],
                    "student_code": user_data.get("student_code"),
                    "faculty": user_data.get("faculty"),
                    "class_name": user_data.get("class_name"),
                    "is_staff": user_data.get("is_staff", False),
                    "is_superuser": user_data.get("is_superuser", False),
                    "is_active": True,
                    "account_status": User.AccountStatus.ACTIVE,
                    "deleted_at": None,
                },
            )
            user.set_password(SEED_PASSWORD)
            user.save(update_fields=["password", "updated_at"])

            role = roles[user_data["role"]]
            UserRole.objects.filter(user=user, is_primary=True).exclude(role=role).update(
                is_primary=False
            )
            UserRole.objects.update_or_create(
                user=user,
                role=role,
                defaults={"is_primary": True, "assigned_by": None},
            )
            users[user.username] = user

        return users

    def _seed_locations(self):
        rooms = {}

        for location_data in SEED_LOCATIONS:
            campus_data = location_data["campus"]
            campus, _ = Campus.all_objects.update_or_create(
                code=campus_data["code"],
                defaults={
                    "name": campus_data["name"],
                    "address": campus_data["address"],
                    "is_active": True,
                    "deleted_at": None,
                },
            )

            for building_data in location_data["buildings"]:
                building, _ = Building.all_objects.update_or_create(
                    campus=campus,
                    code=building_data["code"],
                    defaults={
                        "name": building_data["name"],
                        "is_active": True,
                        "deleted_at": None,
                    },
                )

                for room_data in building_data["rooms"]:
                    room, _ = Room.all_objects.update_or_create(
                        building=building,
                        code=room_data["code"],
                        defaults={
                            "name": room_data["name"],
                            "capacity": room_data["capacity"],
                            "is_active": True,
                            "deleted_at": None,
                        },
                    )
                    rooms[room.code] = room

        return rooms

    def _seed_categories(self):
        categories = {}

        for category_data in SEED_CATEGORIES:
            category, _ = EventCategory.all_objects.update_or_create(
                slug=category_data["slug"],
                defaults={
                    "name": category_data["name"],
                    "description": category_data["description"],
                    "icon": category_data["icon"],
                    "color": category_data["color"],
                    "is_active": True,
                    "deleted_at": None,
                },
            )
            categories[category.slug] = category

        return categories

    def _seed_events(self, organizer, categories, rooms):
        events = {}
        now = timezone.now()

        for event_data in SEED_EVENTS:
            start_at = now + timedelta(days=event_data["starts_in_days"])
            end_at = start_at + timedelta(hours=event_data["duration_hours"])
            room = rooms[event_data["room_code"]]

            event, _ = Event.all_objects.update_or_create(
                slug=event_data["slug"],
                defaults={
                    "category": categories[event_data["category_slug"]],
                    "room": room,
                    "created_by": organizer,
                    "title": event_data["title"],
                    "description": event_data["description"],
                    "visibility": Event.Visibility.PUBLIC,
                    "status": event_data["status"],
                    "registration_open_at": now - timedelta(days=1),
                    "registration_close_at": start_at - timedelta(hours=2),
                    "cancellation_deadline_at": start_at - timedelta(hours=6),
                    "start_at": start_at,
                    "end_at": end_at,
                    "max_capacity": event_data["max_capacity"],
                    "location_snapshot": str(room),
                    "deleted_at": None,
                },
            )

            EventOrganizer.objects.update_or_create(
                event=event,
                user=organizer,
                defaults={"organizer_role": EventOrganizer.OrganizerRole.OWNER},
            )
            self._seed_registration_fields(event, event_data["fields"])
            events[event.slug] = event

        return events

    def _seed_registration_fields(self, event, fields):
        for field_data in fields:
            RegistrationFormField.all_objects.update_or_create(
                event=event,
                field_key=field_data["field_key"],
                defaults={
                    "label": field_data["label"],
                    "field_type": field_data["field_type"],
                    "is_required": field_data.get("is_required", False),
                    "is_editable_after_submit": field_data.get(
                        "is_editable_after_submit", False
                    ),
                    "options_json": field_data.get("options_json", []),
                    "sort_order": field_data.get("sort_order", 0),
                    "deleted_at": None,
                },
            )

    def _seed_registrations(self, events, users):
        for item in SEED_REGISTRATIONS:
            registration, _ = EventRegistration.all_objects.update_or_create(
                event=events[item["event_slug"]],
                user=users[item["username"]],
                defaults={
                    "status": item["status"],
                    "form_answers_jsonb": item["answers"],
                    "answers_locked": False,
                    "deleted_at": None,
                },
            )

            if item["status"] == EventRegistration.RegistrationStatus.REGISTERED:
                self._ensure_ticket(registration)

    def _ensure_ticket(self, registration):
        if hasattr(registration, "ticket"):
            ticket = registration.ticket
            ticket.expires_at = registration.event.end_at
            ticket.status = Ticket.TicketStatus.VALID
            ticket.save(update_fields=["expires_at", "status", "updated_at"])
            return ticket

        ticket_code = generate_ticket_code()
        qr_payload = build_qr_payload(ticket_code)
        return Ticket.objects.create(
            registration=registration,
            ticket_code=ticket_code,
            qr_payload=qr_payload,
            qr_signature=sign_qr_payload(qr_payload),
            status=Ticket.TicketStatus.VALID,
            expires_at=registration.event.end_at,
        )
