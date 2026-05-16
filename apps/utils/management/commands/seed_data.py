from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.app_settings.models import AppSetting
from apps.events.models import (
    Event,
    EventCategory,
    EventInvitation,
    EventOrganizer,
    RegistrationFormField,
)
from apps.interactions.models import EventFeedback, EventQuestion
from apps.locations.models import Building, Campus, Room
from apps.moderation.models import ModerationLog
from apps.notifications.models import Notification, NotificationRecipient, NotificationTemplate
from apps.registrations.models import (
    CheckinLog,
    EventRegistration,
    RegistrationCancellationRequest,
    Ticket,
    TicketQrToken,
)
from apps.registrations.services import (
    build_qr_payload,
    generate_ticket_code,
    hash_token,
    sign_qr_payload,
)
from apps.support.models import SupportMessage, SupportTicket
from apps.users.models import Role, UserAuthIdentity, UserRole, UserSession
from apps.utils.seed_data import (
    LEGACY_SEED_ROLE_CODES,
    SEED_APP_SETTING_KEYS,
    SEED_APP_SETTINGS,
    SEED_BUILDING_CODES,
    SEED_CAMPUS_CODES,
    SEED_CATEGORIES,
    SEED_CATEGORY_SLUGS,
    SEED_CANCELLATION_REQUESTS,
    SEED_CHECKIN_LOGS,
    SEED_EVENTS,
    SEED_EVENT_SLUGS,
    SEED_EVENT_INVITATIONS,
    SEED_FEEDBACKS,
    SEED_INVITATION_TOKENS,
    SEED_LOCATIONS,
    SEED_MODERATION_LOGS,
    SEED_NOTIFICATIONS,
    SEED_NOTIFICATION_TEMPLATE_CODES,
    SEED_NOTIFICATION_TEMPLATES,
    SEED_NOTIFICATION_TITLES,
    SEED_PASSWORD,
    SEED_QUESTIONS,
    SEED_REGISTRATIONS,
    SEED_ROLE_CODES,
    SEED_ROLES,
    SEED_ROOM_CODES,
    SEED_SUPPORT_TICKET_SUBJECTS,
    SEED_SUPPORT_TICKETS,
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
        registrations = self._seed_registrations(events, users)
        self._seed_event_invitations(events, users)
        self._seed_cancellation_requests(events, users, registrations)
        self._seed_checkin_logs(users, registrations)
        self._seed_interactions(events, users)
        self._seed_notifications(events, users)
        self._seed_support(users)
        self._seed_moderation_logs(events, users)
        self._seed_app_settings(users)

        self.stdout.write(
            self.style.SUCCESS(
                "Seed data ready. Login with admin/organizer/student01 using password: "
                f"{SEED_PASSWORD}"
            )
        )

    def _reset_seed_data(self):
        User = get_user_model()

        AppSetting.objects.filter(key__in=SEED_APP_SETTING_KEYS).delete()
        SupportTicket.objects.filter(subject__in=SEED_SUPPORT_TICKET_SUBJECTS).delete()
        Notification.objects.filter(title__in=SEED_NOTIFICATION_TITLES).delete()
        NotificationTemplate.objects.filter(code__in=SEED_NOTIFICATION_TEMPLATE_CODES).delete()
        EventInvitation.objects.filter(token__in=SEED_INVITATION_TOKENS).delete()
        Event.objects.filter(slug__in=SEED_EVENT_SLUGS).delete()
        EventCategory.objects.filter(slug__in=SEED_CATEGORY_SLUGS).delete()
        User.objects.filter(username__in=SEED_USERNAMES).delete()
        Room.objects.filter(code__in=SEED_ROOM_CODES).delete()
        Building.objects.filter(code__in=SEED_BUILDING_CODES).delete()
        Campus.objects.filter(code__in=SEED_CAMPUS_CODES).delete()

        self.stdout.write("Reset existing seed data.")

    def _seed_roles(self):
        roles = {}
        for role_data in SEED_ROLES:
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

        Role.objects.filter(code__in=LEGACY_SEED_ROLE_CODES).exclude(
            code__in=SEED_ROLE_CODES
        ).delete()
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
            self._seed_user_auth(user)

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

    def _seed_user_auth(self, user):
        now = timezone.now()
        UserAuthIdentity.objects.update_or_create(
            provider=UserAuthIdentity.Provider.EMAIL,
            provider_subject=user.email,
            defaults={
                "user": user,
                "email_verified": True,
                "last_login_at": now,
                "deleted_at": None,
            },
        )
        UserSession.objects.update_or_create(
            refresh_token_hash=f"seed-refresh-{user.username}",
            defaults={
                "user": user,
                "device_name": "Seed Browser",
                "ip_address": "127.0.0.1",
                "user_agent": "UEvent seed data",
                "fcm_token": f"seed-fcm-{user.username}",
                "expires_at": now + timedelta(days=30),
                "revoked_at": None,
                "deleted_at": None,
            },
        )

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
        registrations = {}
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
            registrations[(item["event_slug"], item["username"])] = registration

        return registrations

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

    def _seed_event_invitations(self, events, users):
        now = timezone.now()
        for item in SEED_EVENT_INVITATIONS:
            EventInvitation.all_objects.update_or_create(
                event=events[item["event_slug"]],
                email=item["email"],
                defaults={
                    "invited_user": users.get(item["invited_username"]),
                    "token": item["token"],
                    "expires_at": now + timedelta(days=14),
                    "inviter_user": users.get(item["inviter_username"]),
                    "invite_channel": item["invite_channel"],
                    "invite_target": item["email"],
                    "sent_at": now,
                    "responded_at": now if item["status"] != "pending" else None,
                    "status": item["status"],
                    "deleted_at": None,
                },
            )

    def _seed_cancellation_requests(self, events, users, registrations):
        for item in SEED_CANCELLATION_REQUESTS:
            registration = registrations.get((item["event_slug"], item["username"]))
            if not registration:
                continue

            request, _ = RegistrationCancellationRequest.objects.update_or_create(
                registration=registration,
                reason=item["reason"],
                defaults={
                    "event": events[item["event_slug"]],
                    "requester_user": users[item["username"]],
                    "status": item["status"],
                    "reviewed_by_user": None,
                    "reviewed_at": None,
                    "deleted_at": None,
                },
            )
            if registration.status != EventRegistration.RegistrationStatus.CANCELLED:
                registration.status = EventRegistration.RegistrationStatus.CANCEL_PENDING
                registration.save(update_fields=["status", "updated_at"])

    def _seed_checkin_logs(self, users, registrations):
        now = timezone.now()
        for item in SEED_CHECKIN_LOGS:
            registration = registrations.get((item["event_slug"], item["username"]))
            ticket = getattr(registration, "ticket", None) if registration else None
            if not registration or not ticket:
                continue

            if item.get("mark_ticket_used"):
                registration.status = EventRegistration.RegistrationStatus.CHECKED_IN
                registration.save(update_fields=["status", "updated_at"])
                ticket.status = Ticket.TicketStatus.USED
                ticket.used_at = now
                ticket.save(update_fields=["status", "used_at", "updated_at"])

            CheckinLog.objects.update_or_create(
                event=registration.event,
                ticket=ticket,
                result=item["result"],
                defaults={
                    "scanner_user": users.get(item["scanner_username"]),
                    "checked_in_at": now,
                    "note": item["note"],
                    "deleted_at": None,
                },
            )

            raw_token = f"seed-qr-{ticket.ticket_code}"
            TicketQrToken.objects.update_or_create(
                token_hash=hash_token(raw_token),
                defaults={
                    "ticket": ticket,
                    "valid_from": now,
                    "valid_to": now + timedelta(minutes=15),
                    "deleted_at": None,
                },
            )

    def _seed_interactions(self, events, users):
        now = timezone.now()
        for item in SEED_QUESTIONS:
            question, _ = EventQuestion.objects.update_or_create(
                event=events[item["event_slug"]],
                question_text=item["question_text"],
                defaults={
                    "user": users.get(item["username"]),
                    "is_anonymous": item["is_anonymous"],
                    "is_pinned": item["is_pinned"],
                    "answer_text": item["answer_text"] or None,
                    "answered_by": users.get(item["answered_by_username"]),
                    "moderation_status": item["moderation_status"],
                    "asked_at": now - timedelta(days=1),
                    "answered_at": now if item["answer_text"] else None,
                    "deleted_at": None,
                },
            )

        for item in SEED_FEEDBACKS:
            EventFeedback.objects.update_or_create(
                event=events[item["event_slug"]],
                user=users[item["username"]],
                defaults={
                    "rating": item["rating"],
                    "content": item["content"],
                    "is_anonymous": item["is_anonymous"],
                    "deleted_at": None,
                },
            )

    def _seed_notifications(self, events, users):
        now = timezone.now()
        templates = {}
        for item in SEED_NOTIFICATION_TEMPLATES:
            template, _ = NotificationTemplate.all_objects.update_or_create(
                code=item["code"],
                defaults={
                    "name": item["name"],
                    "title_template": item["title_template"],
                    "message_template": item["message_template"],
                    "channel": item["channel"],
                    "is_active": True,
                    "deleted_at": None,
                },
            )
            templates[template.code] = template

        for item in SEED_NOTIFICATIONS:
            notification, _ = Notification.objects.update_or_create(
                title=item["title"],
                defaults={
                    "template": templates.get(item["template_code"]),
                    "event": events.get(item["event_slug"]),
                    "created_by": users.get(item["created_by_username"]),
                    "type": item["type"],
                    "audience_type": item["audience_type"],
                    "message": item["message"],
                    "status": item["status"],
                    "scheduled_at": None,
                    "sent_at": now if item["status"] == Notification.NotificationStatus.SENT else None,
                    "deleted_at": None,
                },
            )

            for username in item["recipient_usernames"]:
                read_at = now if username in item["read_by_usernames"] else None
                NotificationRecipient.objects.update_or_create(
                    notification=notification,
                    user=users[username],
                    defaults={
                        "delivery_status": (
                            NotificationRecipient.DeliveryStatus.READ
                            if read_at
                            else NotificationRecipient.DeliveryStatus.SENT
                        ),
                        "delivered_at": now,
                        "read_at": read_at,
                        "deleted_at": None,
                    },
                )

    def _seed_support(self, users):
        for item in SEED_SUPPORT_TICKETS:
            ticket, _ = SupportTicket.objects.update_or_create(
                subject=item["subject"],
                defaults={
                    "user": users[item["username"]],
                    "category": item["category"],
                    "description": item["description"],
                    "status": item["status"],
                    "priority": item["priority"],
                    "assigned_to": users.get(item["assigned_to_username"]),
                    "deleted_at": None,
                },
            )
            ticket.messages.all().delete()
            for message_data in item["messages"]:
                SupportMessage.objects.create(
                    ticket=ticket,
                    author_user=users.get(message_data["author_username"]),
                    content=message_data["content"],
                    is_staff=message_data["is_staff"],
                )

    def _seed_moderation_logs(self, events, users):
        for item in SEED_MODERATION_LOGS:
            ModerationLog.objects.update_or_create(
                event=events[item["event_slug"]],
                action=item["action"],
                reason=item["reason"],
                defaults={
                    "admin_user": users.get(item["admin_username"]),
                    "report_type": item["report_type"],
                    "deleted_at": None,
                },
            )

    def _seed_app_settings(self, users):
        for item in SEED_APP_SETTINGS:
            AppSetting.all_objects.update_or_create(
                key=item["key"],
                defaults={
                    "value": item["value"],
                    "description": item["description"],
                    "updated_by": users.get(item["updated_by_username"]),
                    "deleted_at": None,
                },
            )
