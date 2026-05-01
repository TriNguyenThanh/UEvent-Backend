from datetime import timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.events.models import Event, EventCategory, EventOrganizer
from apps.registrations.models import EventRegistration, Ticket
from apps.registrations.services import build_qr_payload, sign_qr_payload
from apps.users.models import User


class TicketApiTests(APITestCase):
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
        category = EventCategory.objects.create(name="Tech", slug="tech")
        now = timezone.now()
        self.event = Event.objects.create(
            category=category,
            created_by=self.host,
            title="Demo Event",
            slug="demo-event",
            status=Event.Status.ACTIVE,
            start_at=now - timedelta(hours=1),
            end_at=now + timedelta(hours=2),
        )
        EventOrganizer.objects.create(
            event=self.event,
            user=self.host,
            organizer_role=EventOrganizer.OrganizerRole.OWNER,
        )
        self.registration = EventRegistration.objects.create(
            event=self.event,
            user=self.attendee,
            status=EventRegistration.RegistrationStatus.REGISTERED,
        )

    def test_user_can_list_own_tickets(self):
        qr_payload = build_qr_payload("TK-TEST123")
        Ticket.objects.create(
            registration=self.registration,
            ticket_code="TK-TEST123",
            qr_payload=qr_payload,
            qr_signature=sign_qr_payload(qr_payload),
            status=Ticket.TicketStatus.VALID,
            expires_at=self.event.end_at,
        )

        self.client.force_authenticate(user=self.attendee)
        response = self.client.get("/api/v1/registrations/tickets/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(len(response.data["results"]), 1)

    def test_host_can_create_ticket(self):
        self.client.force_authenticate(user=self.host)
        response = self.client.post(
            "/api/v1/registrations/tickets/",
            {"registration_id": str(self.registration.id)},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], Ticket.TicketStatus.VALID)

    def test_non_host_cannot_create_ticket(self):
        self.client.force_authenticate(user=self.attendee)
        response = self.client.post(
            "/api/v1/registrations/tickets/",
            {"registration_id": str(self.registration.id)},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_checkin_scan_success(self):
        qr_payload = build_qr_payload("TK-CHK123")
        ticket = Ticket.objects.create(
            registration=self.registration,
            ticket_code="TK-CHK123",
            qr_payload=qr_payload,
            qr_signature=sign_qr_payload(qr_payload),
            status=Ticket.TicketStatus.VALID,
            expires_at=self.event.end_at,
        )
        scanner = User.objects.create_user(
            username="scanner",
            password="pass123",
            full_name="Scan User",
        )
        EventOrganizer.objects.create(
            event=self.event,
            user=scanner,
            organizer_role=EventOrganizer.OrganizerRole.CHECKIN,
        )

        self.client.force_authenticate(user=scanner)
        response = self.client.post(
            "/api/v1/registrations/checkin/scan/",
            {"event_id": str(self.event.id), "ticket_code": ticket.ticket_code},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ticket.refresh_from_db()
        self.registration.refresh_from_db()
        self.assertEqual(ticket.status, Ticket.TicketStatus.USED)
        self.assertEqual(
            self.registration.status,
            EventRegistration.RegistrationStatus.CHECKED_IN,
        )
