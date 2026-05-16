import uuid
from datetime import timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.events.models import Event, EventCategory, EventOrganizer
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

    def test_organizer_can_list_own_events(self):
        Event.objects.create(
            category=self.category,
            created_by=self.organizer,
            title="My Event",
            slug="my-event-1",
            **self.valid_times,
        )
        Event.objects.create(
            category=self.category,
            created_by=self.other_organizer,
            title="Other Event",
            slug="other-event-1",
            **self.valid_times,
        )
        self.client.force_authenticate(user=self.organizer)
        response = self.client.get("/api/v1/organizer/events/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)
        self.assertEqual(response.data["data"][0]["title"], "My Event")

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
