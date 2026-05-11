from datetime import timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.events.models import Event, EventCategory
from apps.registrations.models import EventRegistration, Ticket, TicketQrToken
from apps.registrations.services import build_qr_payload, generate_ticket_code, sign_qr_payload
from apps.users.models import User


class RegistrationApiTests(APITestCase):
    def setUp(self):
        self.host = User.objects.create_user(
            username="host",
            password="pass123",
            full_name="Host User",
        )
        self.attendee = User.objects.create_user(
            username="attendee",
            password="pass123",
            full_name="Attendee User",
        )
        category = EventCategory.objects.create(name="Workshop", slug="workshop")
        now = timezone.now()
        self.event = Event.objects.create(
            category=category,
            created_by=self.host,
            title="Career Workshop",
            slug="career-workshop",
            status=Event.Status.APPROVED,
            registration_open_at=now - timedelta(days=1),
            registration_close_at=now + timedelta(days=1),
            start_at=now + timedelta(days=2),
            end_at=now + timedelta(days=2, hours=2),
            max_capacity=10,
        )

    def test_user_can_register_for_event(self):
        self.client.force_authenticate(user=self.attendee)

        response = self.client.post(
            "/api/v1/registrations/",
            {"event_id": str(self.event.id)},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], EventRegistration.RegistrationStatus.REGISTERED)
        self.assertIsNotNone(response.data["ticket"])

    def test_registration_list_returns_only_current_user_items(self):
        EventRegistration.objects.create(
            event=self.event,
            user=self.attendee,
            status=EventRegistration.RegistrationStatus.WAITLISTED,
        )
        other_user = User.objects.create_user(username="other", password="pass123")
        EventRegistration.objects.create(
            event=self.event,
            user=other_user,
            status=EventRegistration.RegistrationStatus.WAITLISTED,
        )

        self.client.force_authenticate(user=self.attendee)
        response = self.client.get("/api/v1/registrations/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["event"]["id"], str(self.event.id))

    def test_registration_becomes_waitlisted_when_event_is_full(self):
        self.event.max_capacity = 1
        self.event.save(update_fields=["max_capacity", "updated_at"])
        registered_user = User.objects.create_user(username="registered", password="pass123")
        EventRegistration.objects.create(
            event=self.event,
            user=registered_user,
            status=EventRegistration.RegistrationStatus.REGISTERED,
        )

        self.client.force_authenticate(user=self.attendee)
        response = self.client.post(
            "/api/v1/registrations/",
            {"event_id": str(self.event.id)},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], EventRegistration.RegistrationStatus.WAITLISTED)
        self.assertIsNone(response.data["ticket"])

    def test_user_can_get_rotating_qr_payload(self):
        registration = EventRegistration.objects.create(
            event=self.event,
            user=self.attendee,
            status=EventRegistration.RegistrationStatus.REGISTERED,
        )

        ticket_code = generate_ticket_code()
        qr_payload = build_qr_payload(ticket_code)
        Ticket.objects.create(
            registration=registration,
            ticket_code=ticket_code,
            qr_payload=qr_payload,
            qr_signature=sign_qr_payload(qr_payload),
            status=Ticket.TicketStatus.VALID,
            expires_at=self.event.end_at,
        )

        self.client.force_authenticate(user=self.attendee)
        response = self.client.get(f"/api/v1/registrations/{registration.id}/qr/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("qr_payload", response.data)
        self.assertIn("qr_signature", response.data)
        self.assertEqual(
            TicketQrToken.objects.filter(ticket__registration=registration).count(),
            1,
        )
