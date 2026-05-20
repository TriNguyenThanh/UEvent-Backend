import uuid
from datetime import timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.events.models import Event, EventCategory, EventOrganizer
from apps.locations.models import Building, Campus, Room
from apps.registrations.models import EventRegistration
from apps.users.models import User


class TestOrganizerEventCRUD(APITestCase):
    def setUp(self):
        self.organizer = User.objects.create_user(
            username="organizer",
            password="pass123",
            full_name="Organizer User",
        )
        self.other_organizer = User.objects.create_user(
            username="other_organizer",
            password="pass123",
            full_name="Other Organizer",
        )
        self.category = EventCategory.objects.create(
            name="Workshop",
            slug="workshop",
            is_active=True,
        )
        self.inactive_category = EventCategory.objects.create(
            name="Inactive",
            slug="inactive",
            is_active=False,
        )
        now = timezone.now()
        self.valid_times = {
            "start_at": (now + timedelta(days=5)).isoformat(),
            "end_at": (now + timedelta(days=5, hours=2)).isoformat(),
        }

    def test_organizer_can_create_event(self):
        self.client.force_authenticate(user=self.organizer)
        response = self.client.post(
            "/api/v1/organizer/events/",
            {
                "title": "My Workshop",
                "category": str(self.category.id),
                **self.valid_times,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["data"]["title"], "My Workshop")
        self.assertEqual(response.data["data"]["status"], Event.Status.DRAFT)

    def test_create_event_auto_generates_slug(self):
        self.client.force_authenticate(user=self.organizer)
        response = self.client.post(
            "/api/v1/organizer/events/",
            {
                "title": "Test Event 123",
                "category": str(self.category.id),
                **self.valid_times,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["data"]["slug"].startswith("test-event-123"))

    def test_create_event_creates_owner_organizer_row(self):
        self.client.force_authenticate(user=self.organizer)
        response = self.client.post(
            "/api/v1/organizer/events/",
            {
                "title": "Owner Event",
                "category": str(self.category.id),
                **self.valid_times,
            },
            format="json",
        )
        event_id = response.data["data"]["id"]
        self.assertTrue(
            EventOrganizer.objects.filter(
                event_id=event_id,
                user=self.organizer,
                organizer_role=EventOrganizer.OrganizerRole.OWNER,
            ).exists()
        )

    def test_organizer_can_list_events_by_owner_cohost_staff_roles(self):
        owner_event = Event.objects.create(
            category=self.category,
            created_by=self.organizer,
            title="Owner Event",
            slug="owner-event-1",
            **self.valid_times,
        )
        cohost_event = Event.objects.create(
            category=self.category,
            created_by=self.other_organizer,
            title="Cohost Event",
            slug="cohost-event-1",
            **self.valid_times,
        )
        staff_event = Event.objects.create(
            category=self.category,
            created_by=self.other_organizer,
            title="Staff Event",
            slug="staff-event-1",
            **self.valid_times,
        )
        checkin_event = Event.objects.create(
            category=self.category,
            created_by=self.other_organizer,
            title="Checkin Event",
            slug="checkin-event-1",
            **self.valid_times,
        )
        Event.objects.create(
            category=self.category,
            created_by=self.other_organizer,
            title="Other Event",
            slug="other-event-1",
            **self.valid_times,
        )
        EventOrganizer.objects.create(
            event=owner_event,
            user=self.organizer,
            organizer_role=EventOrganizer.OrganizerRole.OWNER,
        )
        EventOrganizer.objects.create(
            event=cohost_event,
            user=self.organizer,
            organizer_role=EventOrganizer.OrganizerRole.CO_HOST,
        )
        EventOrganizer.objects.create(
            event=staff_event,
            user=self.organizer,
            organizer_role=EventOrganizer.OrganizerRole.STAFF,
        )
        EventOrganizer.objects.create(
            event=checkin_event,
            user=self.organizer,
            organizer_role=EventOrganizer.OrganizerRole.CHECKIN,
        )
        self.client.force_authenticate(user=self.organizer)
        response = self.client.get("/api/v1/organizer/events/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 3)
        self.assertEqual(
            {event["title"] for event in response.data["data"]},
            {"Owner Event", "Cohost Event", "Staff Event"},
        )

    def test_organizer_can_retrieve_event_detail(self):
        event = Event.objects.create(
            category=self.category,
            created_by=self.organizer,
            title="My Event",
            slug="my-event-detail",
            description="Description",
            **self.valid_times,
        )
        self.client.force_authenticate(user=self.organizer)
        response = self.client.get(f"/api/v1/organizer/events/{event.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["title"], "My Event")
        self.assertIn("organizers", response.data["data"])
        self.assertIn("registration_fields", response.data["data"])

    def test_organizer_can_patch_event(self):
        event = Event.objects.create(
            category=self.category,
            created_by=self.organizer,
            title="Original Title",
            slug="patch-event-1",
            **self.valid_times,
        )
        self.client.force_authenticate(user=self.organizer)
        response = self.client.patch(
            f"/api/v1/organizer/events/{event.id}/",
            {"title": "Updated Title", "description": "New description"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["title"], "Updated Title")

    def test_organizer_can_patch_event_category_and_clear_room(self):
        new_category = EventCategory.objects.create(
            name="Conference",
            slug="conference",
            is_active=True,
        )
        campus = Campus.objects.create(name="Main Campus", code="MAIN")
        building = Building.objects.create(name="Main Building", code="MB", campus=campus)
        room = Room.objects.create(name="Auditorium", code="A1", building=building)
        event = Event.objects.create(
            category=self.category,
            room=room,
            created_by=self.organizer,
            title="Original Title",
            slug="patch-event-category-room",
            **self.valid_times,
        )

        self.client.force_authenticate(user=self.organizer)
        response = self.client.patch(
            f"/api/v1/organizer/events/{event.id}/",
            {"category": str(new_category.id), "room": None},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        event.refresh_from_db()
        self.assertEqual(event.category_id, new_category.id)
        self.assertIsNone(event.room_id)

    def test_organizer_can_delete_event(self):
        event = Event.objects.create(
            category=self.category,
            created_by=self.organizer,
            title="Delete Me",
            slug="delete-event-1",
            **self.valid_times,
        )
        self.client.force_authenticate(user=self.organizer)
        response = self.client.delete(f"/api/v1/organizer/events/{event.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Verify soft delete: default manager excludes deleted, so use all_objects
        event = Event.all_objects.get(pk=event.pk)
        self.assertIsNotNone(event.deleted_at)

    def test_non_organizer_cannot_access_other_event(self):
        event = Event.objects.create(
            category=self.category,
            created_by=self.other_organizer,
            title="Other Event",
            slug="other-event-access",
            **self.valid_times,
        )
        self.client.force_authenticate(user=self.organizer)
        response = self.client.get(f"/api/v1/organizer/events/{event.id}/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self.client.patch(
            f"/api/v1/organizer/events/{event.id}/",
            {"title": "Hacked"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self.client.delete(f"/api/v1/organizer/events/{event.id}/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_anonymous_user_gets_401(self):
        response = self.client.get("/api/v1/organizer/events/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_end_before_start_returns_error(self):
        now = timezone.now()
        self.client.force_authenticate(user=self.organizer)
        response = self.client.post(
            "/api/v1/organizer/events/",
            {
                "title": "Bad Dates",
                "category": str(self.category.id),
                "start_at": (now + timedelta(days=5)).isoformat(),
                "end_at": (now + timedelta(days=4)).isoformat(),
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_registration_close_after_start_returns_error(self):
        now = timezone.now()
        self.client.force_authenticate(user=self.organizer)
        response = self.client.post(
            "/api/v1/organizer/events/",
            {
                "title": "Bad Reg Close",
                "category": str(self.category.id),
                "start_at": (now + timedelta(days=5)).isoformat(),
                "end_at": (now + timedelta(days=5, hours=2)).isoformat(),
                "registration_open_at": (now + timedelta(days=1)).isoformat(),
                "registration_close_at": (now + timedelta(days=6)).isoformat(),
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_inactive_category_returns_error(self):
        self.client.force_authenticate(user=self.organizer)
        response = self.client.post(
            "/api/v1/organizer/events/",
            {
                "title": "Inactive Category",
                "category": str(self.inactive_category.id),
                **self.valid_times,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_nonexistent_category_returns_error(self):
        self.client.force_authenticate(user=self.organizer)
        response = self.client.post(
            "/api/v1/organizer/events/",
            {
                "title": "No Category",
                "category": str(uuid.uuid4()),
                **self.valid_times,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_anonymous_user_can_search_public_events(self):
        Event.objects.create(
            category=self.category,
            created_by=self.organizer,
            title="Public Workshop",
            slug="public-workshop",
            description="Learn Django APIs",
            visibility=Event.Visibility.PUBLIC,
            status=Event.Status.APPROVED,
            **self.valid_times,
        )
        Event.objects.create(
            category=self.category,
            created_by=self.organizer,
            title="Draft Public Event",
            slug="draft-public-event",
            visibility=Event.Visibility.PUBLIC,
            status=Event.Status.DRAFT,
            **self.valid_times,
        )
        Event.objects.create(
            category=self.category,
            created_by=self.organizer,
            title="Private Workshop",
            slug="private-workshop",
            visibility=Event.Visibility.PRIVATE,
            status=Event.Status.APPROVED,
            **self.valid_times,
        )

        response = self.client.get("/api/v1/events/search/", {"search": "workshop"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)
        self.assertEqual(response.data["data"][0]["title"], "Public Workshop")

    def test_authenticated_user_can_search_public_events_regardless_role(self):
        Event.objects.create(
            category=self.category,
            created_by=self.other_organizer,
            title="Active Public Event",
            slug="active-public-event",
            description="Open to everyone",
            visibility=Event.Visibility.PUBLIC,
            status=Event.Status.ACTIVE,
            **self.valid_times,
        )
        attendee = User.objects.create_user(username="attendee", password="pass123")
        self.client.force_authenticate(user=attendee)

        response = self.client.get("/api/v1/events/search/", {"q": "everyone"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)
        self.assertEqual(response.data["data"][0]["title"], "Active Public Event")

    def test_user_event_highlights_prioritizes_registered_events_regardless_status(self):
        attendee = User.objects.create_user(username="attendee", password="pass123")
        registered_event = Event.objects.create(
            category=self.category,
            created_by=self.organizer,
            title="Registered Event",
            slug="highlight-registered-event",
            **self.valid_times,
        )
        rejected_event = Event.objects.create(
            category=self.category,
            created_by=self.organizer,
            title="Rejected Registration Event",
            slug="highlight-rejected-registration-event",
            **self.valid_times,
        )
        Event.objects.create(
            category=self.category,
            created_by=attendee,
            title="Created Event",
            slug="highlight-created-event",
            **self.valid_times,
        )
        EventRegistration.objects.create(
            event=registered_event,
            user=attendee,
            status=EventRegistration.RegistrationStatus.REGISTERED,
        )
        EventRegistration.objects.create(
            event=rejected_event,
            user=attendee,
            status=EventRegistration.RegistrationStatus.REJECTED,
        )

        self.client.force_authenticate(user=attendee)
        response = self.client.get("/api/v1/events/me/highlights/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 2)
        self.assertEqual(
            {event["title"] for event in response.data["data"]},
            {"Registered Event", "Rejected Registration Event"},
        )

    def test_user_event_highlights_fills_with_created_events_when_needed(self):
        attendee = User.objects.create_user(username="attendee", password="pass123")
        registered_event = Event.objects.create(
            category=self.category,
            created_by=self.organizer,
            title="Only Registered Event",
            slug="highlight-only-registered-event",
            **self.valid_times,
        )
        created_event = Event.objects.create(
            category=self.category,
            created_by=attendee,
            title="Created Fallback Event",
            slug="highlight-created-fallback-event",
            **self.valid_times,
        )
        EventRegistration.objects.create(
            event=registered_event,
            user=attendee,
            status=EventRegistration.RegistrationStatus.CANCELLED,
        )

        self.client.force_authenticate(user=attendee)
        response = self.client.get("/api/v1/events/me/highlights/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [event["title"] for event in response.data["data"]],
            ["Only Registered Event", "Created Fallback Event"],
        )
        self.assertEqual(response.data["data"][1]["id"], str(created_event.id))

    def test_public_event_search_filters_category_by_slug(self):
        other_category = EventCategory.objects.create(
            name="Conference",
            slug="conference",
            is_active=True,
        )
        Event.objects.create(
            category=self.category,
            created_by=self.organizer,
            title="Workshop Event",
            slug="category-workshop-event",
            visibility=Event.Visibility.PUBLIC,
            status=Event.Status.ACTIVE,
            **self.valid_times,
        )
        Event.objects.create(
            category=other_category,
            created_by=self.organizer,
            title="Conference Event",
            slug="category-conference-event",
            visibility=Event.Visibility.PUBLIC,
            status=Event.Status.ACTIVE,
            **self.valid_times,
        )

        response = self.client.get("/api/v1/events/search/", {"category": "workshop"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)
        self.assertEqual(response.data["data"][0]["title"], "Workshop Event")

    def test_public_event_search_filters_category_by_name(self):
        Event.objects.create(
            category=self.category,
            created_by=self.organizer,
            title="Workshop Name Event",
            slug="category-workshop-name-event",
            visibility=Event.Visibility.PUBLIC,
            status=Event.Status.ACTIVE,
            **self.valid_times,
        )

        response = self.client.get("/api/v1/events/search/", {"category": "work"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)
        self.assertEqual(response.data["data"][0]["title"], "Workshop Name Event")

    def test_public_event_search_allows_blank_category(self):
        Event.objects.create(
            category=self.category,
            created_by=self.organizer,
            title="Blank Category Event",
            slug="blank-category-event",
            visibility=Event.Visibility.PUBLIC,
            status=Event.Status.ACTIVE,
            **self.valid_times,
        )

        response = self.client.get(
            "/api/v1/events/search/",
            {"page": 1, "page_size": 2, "category": "", "status": "active"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)
        self.assertEqual(response.data["data"][0]["title"], "Blank Category Event")

    def test_anonymous_user_can_list_active_event_categories(self):
        response = self.client.get("/api/v1/event-categories/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)
        self.assertEqual(response.data["data"][0]["name"], "Workshop")
        self.assertIn("description", response.data["data"][0])
