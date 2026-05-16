from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.test import APITestCase

from common.exceptions import ConflictError
from apps.events.models import Event, EventCategory, EventOrganizer
from apps.registrations.models import EventRegistration, Ticket, TicketQrToken
from apps.registrations.services import (
    build_qr_payload,
    cancel_event_registration,
    create_event_registration,
    generate_ticket_code,
    issue_registration_qr,
    process_checkin_scan,
    sign_qr_payload,
)
from apps.users.models import User


class RegistrationTestMixin:
    password = "pass123"

    def setUp(self):
        self.now = timezone.now()
        self.host = self.create_user("host", full_name="Host User")
        self.attendee = self.create_user("attendee", full_name="Attendee User")
        self.other_user = self.create_user("other", full_name="Other User")
        self.category = EventCategory.objects.create(name="Workshop", slug="workshop")
        self.event = self.create_event()

    def create_user(self, username, **extra_fields):
        return User.objects.create_user(username=username, password=self.password, **extra_fields)

    def create_event(self, **overrides):
        index = Event.objects.count() + 1
        defaults = {
            "category": self.category,
            "created_by": self.host,
            "title": f"Career Workshop {index}",
            "slug": f"career-workshop-{index}",
            "status": Event.Status.APPROVED,
            "registration_open_at": self.now - timedelta(days=1),
            "registration_close_at": self.now + timedelta(days=1),
            "start_at": self.now + timedelta(days=2),
            "end_at": self.now + timedelta(days=2, hours=2),
            "max_capacity": 10,
        }
        defaults.update(overrides)
        return Event.objects.create(**defaults)

    def create_registration(self, user=None, event=None, status_value=None, answers=None):
        return EventRegistration.objects.create(
            event=event or self.event,
            user=user or self.attendee,
            status=status_value or EventRegistration.RegistrationStatus.REGISTERED,
            form_answers_jsonb=answers if answers is not None else [],
        )

    def create_ticket(self, registration=None, status_value=None, expires_at=None):
        registration = registration or self.create_registration()
        ticket_code = generate_ticket_code()
        qr_payload = build_qr_payload(ticket_code)
        return Ticket.objects.create(
            registration=registration,
            ticket_code=ticket_code,
            qr_payload=qr_payload,
            qr_signature=sign_qr_payload(qr_payload),
            status=status_value or Ticket.TicketStatus.VALID,
            expires_at=expires_at or registration.event.end_at,
        )

    def add_organizer(self, user=None, event=None, role=None):
        return EventOrganizer.objects.create(
            event=event or self.event,
            user=user or self.host,
            organizer_role=role or EventOrganizer.OrganizerRole.OWNER,
        )


class RegistrationServiceTests(RegistrationTestMixin, APITestCase):
    def test_create_event_registration_issues_ticket_for_available_event(self):
        registration = create_event_registration(
            user=self.attendee,
            event_id=self.event.id,
            answers=[{"fieldId": "shirt_size", "value": "L"}],
        )

        self.assertEqual(registration.status, EventRegistration.RegistrationStatus.REGISTERED)
        self.assertEqual(registration.form_answers_jsonb, [{"fieldId": "shirt_size", "value": "L"}])
        self.assertTrue(hasattr(registration, "ticket"))
        self.assertEqual(registration.ticket.status, Ticket.TicketStatus.VALID)
        self.assertEqual(registration.ticket.expires_at, self.event.end_at)

    def test_create_event_registration_waitlists_when_capacity_is_full(self):
        self.event.max_capacity = 1
        self.event.save(update_fields=["max_capacity", "updated_at"])
        self.create_registration(user=self.other_user)

        registration = create_event_registration(user=self.attendee, event_id=self.event.id)

        self.assertEqual(registration.status, EventRegistration.RegistrationStatus.WAITLISTED)
        self.assertFalse(Ticket.objects.filter(registration=registration).exists())

    def test_create_event_registration_rejects_duplicate_registration(self):
        self.create_registration(user=self.attendee)

        with self.assertRaises(ConflictError):
            create_event_registration(user=self.attendee, event_id=self.event.id)

    def test_create_event_registration_validates_registration_window(self):
        not_open_event = self.create_event(
            registration_open_at=self.now + timedelta(hours=1),
            registration_close_at=self.now + timedelta(days=2),
            slug="future-registration",
        )
        closed_event = self.create_event(
            registration_open_at=self.now - timedelta(days=3),
            registration_close_at=self.now - timedelta(hours=1),
            slug="closed-registration",
        )
        ended_event = self.create_event(
            registration_open_at=self.now - timedelta(days=3),
            registration_close_at=self.now + timedelta(days=1),
            start_at=self.now - timedelta(days=2),
            end_at=self.now - timedelta(days=1),
            slug="ended-event",
        )

        with self.assertRaises(ValidationError):
            create_event_registration(user=self.attendee, event_id=not_open_event.id)
        with self.assertRaises(ValidationError):
            create_event_registration(user=self.attendee, event_id=closed_event.id)
        with self.assertRaises(ValidationError):
            create_event_registration(user=self.attendee, event_id=ended_event.id)
        with self.assertRaises(NotFound):
            create_event_registration(user=self.attendee, event_id="00000000-0000-0000-0000-000000000000")

    def test_cancel_event_registration_cancels_related_ticket_and_stores_reason(self):
        registration = self.create_registration()
        ticket = self.create_ticket(registration)

        cancelled = cancel_event_registration(registration=registration, reason="Capacity changed")

        registration.refresh_from_db()
        ticket.refresh_from_db()
        self.assertEqual(cancelled.status, EventRegistration.RegistrationStatus.CANCELLED)
        self.assertIsNotNone(registration.cancelled_at)
        self.assertEqual(registration.cancel_reason, "Capacity changed")
        self.assertEqual(ticket.status, Ticket.TicketStatus.CANCELLED)

    def test_cancel_event_registration_rejects_already_cancelled_registration(self):
        registration = self.create_registration(status_value=EventRegistration.RegistrationStatus.CANCELLED)

        with self.assertRaises(ValidationError):
            cancel_event_registration(registration=registration)

    def test_issue_registration_qr_creates_short_lived_token_payload(self):
        registration = self.create_registration()
        ticket = self.create_ticket(registration)

        qr_data = issue_registration_qr(registration=registration)

        token = TicketQrToken.objects.get(ticket=ticket)
        self.assertEqual(qr_data["registration_id"], registration.id)
        self.assertEqual(qr_data["event_id"], self.event.id)
        self.assertEqual(qr_data["ticket_id"], ticket.id)
        self.assertEqual(qr_data["ticket_code"], ticket.ticket_code)
        self.assertTrue(qr_data["qr_payload"].startswith("TICKET:"))
        self.assertEqual(sign_qr_payload(qr_data["qr_payload"]), qr_data["qr_signature"])
        self.assertLessEqual((token.valid_to - token.valid_from).total_seconds(), 15)

    def test_process_checkin_scan_marks_ticket_used_and_registration_checked_in(self):
        active_event = self.create_event(
            status=Event.Status.ACTIVE,
            registration_open_at=self.now - timedelta(days=3),
            registration_close_at=self.now + timedelta(days=1),
            start_at=self.now - timedelta(hours=1),
            end_at=self.now + timedelta(hours=2),
            slug="active-event",
        )
        registration = self.create_registration(event=active_event)
        ticket = self.create_ticket(registration)

        result = process_checkin_scan(
            event_id=active_event.id,
            ticket_code=ticket.ticket_code,
            qr_payload=None,
            qr_signature=None,
            scanner_user=self.host,
        )

        registration.refresh_from_db()
        ticket.refresh_from_db()
        self.assertEqual(result["result"], "success")
        self.assertEqual(ticket.status, Ticket.TicketStatus.USED)
        self.assertEqual(registration.status, EventRegistration.RegistrationStatus.CHECKED_IN)
        self.assertIsNotNone(ticket.used_at)


class RegistrationApiTests(RegistrationTestMixin, APITestCase):
    def event_registrations_url(self, event=None):
        return reverse("event-registration-list-create", kwargs={"event_id": (event or self.event).id})

    def event_registration_detail_url(self, registration, event=None):
        return reverse(
            "event-registration-detail",
            kwargs={"event_id": (event or self.event).id, "registration_id": registration.id},
        )

    def event_registration_cancel_url(self, registration, event=None):
        return reverse(
            "event-registration-cancel",
            kwargs={"event_id": (event or self.event).id, "registration_id": registration.id},
        )

    def my_event_registration_cancel_url(self, event=None):
        return reverse("event-registration-me-cancel", kwargs={"event_id": (event or self.event).id})

    def ticket_detail_url(self, ticket):
        return reverse("ticket-detail", kwargs={"ticket_id": ticket.id})

    def ticket_qr_url(self, ticket):
        return reverse("ticket-qr", kwargs={"ticket_id": ticket.id})

    def ticket_cancel_url(self, ticket):
        return reverse("ticket-cancel", kwargs={"ticket_id": ticket.id})

    def authenticate(self, user=None):
        self.client.force_authenticate(user=user or self.attendee)

    def test_authenticated_user_can_register_for_event(self):
        self.authenticate()

        response = self.client.post(
            self.event_registrations_url(),
            {"answers": [{"fieldId": "shirt_size", "value": "L"}]},
            format="json",
        )

        registration = EventRegistration.objects.get(event=self.event, user=self.attendee)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["id"], str(registration.id))
        self.assertEqual(response.data["status"], EventRegistration.RegistrationStatus.REGISTERED)
        self.assertEqual(response.data["answers"], [{"fieldId": "shirt_size", "value": "L"}])
        self.assertEqual(response.data["event"]["id"], str(self.event.id))
        self.assertEqual(response.data["user"]["id"], str(self.attendee.id))
        self.assertIsNotNone(response.data["ticket"])
        self.assertTrue(Ticket.objects.filter(registration=registration).exists())

    def test_register_returns_waitlisted_without_ticket_when_event_is_full(self):
        self.event.max_capacity = 1
        self.event.save(update_fields=["max_capacity", "updated_at"])
        self.create_registration(user=self.other_user)
        self.authenticate()

        response = self.client.post(self.event_registrations_url(), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], EventRegistration.RegistrationStatus.WAITLISTED)
        self.assertIsNone(response.data["ticket"])

    def test_register_returns_conflict_for_duplicate_registration(self):
        self.create_registration(user=self.attendee)
        self.authenticate()

        response = self.client.post(self.event_registrations_url(), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("already registered", response.data["message"])

    def test_organizer_can_list_and_retrieve_event_registrations(self):
        registration = self.create_registration(user=self.attendee)
        self.add_organizer(user=self.host)
        self.authenticate(self.host)

        list_response = self.client.get(self.event_registrations_url())
        detail_response = self.client.get(self.event_registration_detail_url(registration))

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(list_response.data["count"], 1)
        self.assertEqual(list_response.data["results"][0]["user"]["id"], str(self.attendee.id))
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.data["id"], str(registration.id))

    def test_event_creator_can_list_registrations_without_explicit_organizer_role(self):
        self.create_registration(user=self.attendee)
        self.authenticate(self.host)

        response = self.client.get(self.event_registrations_url())

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    def test_non_organizer_cannot_list_or_retrieve_event_registrations(self):
        registration = self.create_registration(user=self.attendee)
        self.authenticate(self.other_user)

        list_response = self.client.get(self.event_registrations_url())
        detail_response = self.client.get(self.event_registration_detail_url(registration))

        self.assertEqual(list_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(detail_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_registration_list_returns_only_current_user_items(self):
        self.create_registration(user=self.attendee, status_value=EventRegistration.RegistrationStatus.WAITLISTED)
        self.create_registration(user=self.other_user, status_value=EventRegistration.RegistrationStatus.WAITLISTED)
        self.authenticate()

        response = self.client.get(reverse("registration-me-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["user"]["id"], str(self.attendee.id))

    def test_user_can_cancel_own_event_registration(self):
        registration = self.create_registration()
        ticket = self.create_ticket(registration)
        self.authenticate()

        response = self.client.delete(self.my_event_registration_cancel_url())

        registration.refresh_from_db()
        ticket.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(registration.status, EventRegistration.RegistrationStatus.CANCELLED)
        self.assertEqual(ticket.status, Ticket.TicketStatus.CANCELLED)

    def test_user_cannot_cancel_another_users_event_registration(self):
        self.create_registration(user=self.other_user)
        self.authenticate()

        response = self.client.delete(self.my_event_registration_cancel_url())

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_organizer_can_cancel_registration_with_reason(self):
        registration = self.create_registration()
        self.add_organizer(user=self.host)
        self.authenticate(self.host)

        response = self.client.patch(
            self.event_registration_cancel_url(registration),
            {"reason": "Capacity changed"},
            format="json",
        )

        registration.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(registration.status, EventRegistration.RegistrationStatus.CANCELLED)
        self.assertEqual(registration.cancel_reason, "Capacity changed")

    def test_non_organizer_cannot_cancel_event_registration(self):
        registration = self.create_registration()
        self.authenticate(self.other_user)

        response = self.client.patch(
            self.event_registration_cancel_url(registration),
            {"reason": "No access"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_user_can_list_retrieve_and_get_qr_for_own_ticket(self):
        registration = self.create_registration()
        ticket = self.create_ticket(registration)
        self.authenticate()

        list_response = self.client.get(reverse("ticket-me-list"))
        detail_response = self.client.get(self.ticket_detail_url(ticket))
        qr_response = self.client.get(self.ticket_qr_url(ticket))

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(list_response.data["count"], 1)
        self.assertEqual(list_response.data["results"][0]["id"], str(ticket.id))
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.data["id"], str(ticket.id))
        self.assertEqual(qr_response.status_code, status.HTTP_200_OK)
        self.assertEqual(qr_response.data["ticket_id"], str(ticket.id))
        self.assertTrue(qr_response.data["qr_payload"].startswith("TICKET:"))
        self.assertEqual(TicketQrToken.objects.filter(ticket=ticket).count(), 1)

    def test_organizer_can_retrieve_and_get_qr_for_event_ticket(self):
        registration = self.create_registration()
        ticket = self.create_ticket(registration)
        self.add_organizer(user=self.host)
        self.authenticate(self.host)

        detail_response = self.client.get(self.ticket_detail_url(ticket))
        qr_response = self.client.get(self.ticket_qr_url(ticket))

        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.data["id"], str(ticket.id))
        self.assertEqual(qr_response.status_code, status.HTTP_200_OK)

    def test_unrelated_user_cannot_access_ticket_detail_or_qr(self):
        registration = self.create_registration()
        ticket = self.create_ticket(registration)
        self.authenticate(self.other_user)

        detail_response = self.client.get(self.ticket_detail_url(ticket))
        qr_response = self.client.get(self.ticket_qr_url(ticket))

        self.assertEqual(detail_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(qr_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_ticket_cancel_endpoint_cancels_registration_and_ticket(self):
        registration = self.create_registration()
        ticket = self.create_ticket(registration)
        self.authenticate()

        response = self.client.patch(
            self.ticket_cancel_url(ticket),
            {"reason": "Cannot attend"},
            format="json",
        )

        registration.refresh_from_db()
        ticket.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(registration.status, EventRegistration.RegistrationStatus.CANCELLED)
        self.assertEqual(registration.cancel_reason, "Cannot attend")
        self.assertEqual(ticket.status, Ticket.TicketStatus.CANCELLED)

    def test_qr_endpoint_rejects_waitlisted_registration_without_ticket(self):
        registration = self.create_registration(status_value=EventRegistration.RegistrationStatus.WAITLISTED)
        self.authenticate()

        response = self.client.get(
            reverse("ticket-qr", kwargs={"ticket_id": "00000000-0000-0000-0000-000000000000"})
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(Ticket.objects.filter(registration=registration).exists())
