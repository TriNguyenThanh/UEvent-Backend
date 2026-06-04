import uuid
from datetime import timedelta
from unittest.mock import Mock, patch

from django.core.cache import cache
from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.events.models import (
    Event,
    EventCategory,
    EventOrganizer,
    RegistrationFormField,
)
from apps.locations.models import Building, Campus, Room
from apps.registrations.models import EventRegistration
from apps.users.models import User


class TestOrganizerEventCRUD(APITestCase):
    def setUp(self):
        cache.clear()
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
        self.assertTrue(
            all(event["isOrganizer"] is True for event in response.data["data"])
        )

    def test_organizer_can_retrieve_event_detail(self):
        self.organizer.avatar_url = "https://cdn.test/organizer-avatar.png"
        self.organizer.save(update_fields=["avatar_url", "updated_at"])
        event = Event.objects.create(
            category=self.category,
            created_by=self.organizer,
            title="My Event",
            slug="my-event-detail",
            description="Description",
            **self.valid_times,
        )
        EventOrganizer.objects.create(
            event=event,
            user=self.organizer,
            organizer_role=EventOrganizer.OrganizerRole.OWNER,
        )
        self.client.force_authenticate(user=self.organizer)
        response = self.client.get(f"/api/v1/organizer/events/{event.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["title"], "My Event")
        self.assertEqual(
            response.data["data"]["created_by"]["avatar_url"],
            "https://cdn.test/organizer-avatar.png",
        )
        self.assertIn("organizers", response.data["data"])
        self.assertEqual(
            response.data["data"]["organizers"][0]["user"]["avatar_url"],
            "https://cdn.test/organizer-avatar.png",
        )
        self.assertIn("registration_fields", response.data["data"])

    def test_owner_can_add_and_remove_event_organizer_by_email(self):
        member = User.objects.create_user(
            username="team_member",
            email="team@example.com",
            password="pass123",
            full_name="Team Member",
        )
        event = Event.objects.create(
            category=self.category,
            created_by=self.organizer,
            title="Team Event",
            slug="team-event",
            **self.valid_times,
        )
        EventOrganizer.objects.create(
            event=event,
            user=self.organizer,
            organizer_role=EventOrganizer.OrganizerRole.OWNER,
        )

        self.client.force_authenticate(user=self.organizer)
        response = self.client.post(
            f"/api/v1/organizer/events/{event.id}/organizers/",
            {"email": "TEAM@example.com"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["user"]["email"], member.email)
        self.assertEqual(
            response.data["data"]["organizer_role"],
            EventOrganizer.OrganizerRole.CO_HOST,
        )

        delete_response = self.client.delete(
            f"/api/v1/organizer/events/{event.id}/organizers/",
            {"email": "team@example.com"},
            format="json",
        )
        self.assertEqual(delete_response.status_code, status.HTTP_200_OK)
        self.assertFalse(
            EventOrganizer.objects.filter(event=event, user=member).exists()
        )

    def test_owner_can_readd_soft_deleted_event_organizer_by_email(self):
        member = User.objects.create_user(
            username="team_member_readd",
            email="team-readd@example.com",
            password="pass123",
            full_name="Team Readd",
        )
        event = Event.objects.create(
            category=self.category,
            created_by=self.organizer,
            title="Team Readd Event",
            slug="team-readd-event",
            **self.valid_times,
        )
        EventOrganizer.objects.create(
            event=event,
            user=self.organizer,
            organizer_role=EventOrganizer.OrganizerRole.OWNER,
        )

        self.client.force_authenticate(user=self.organizer)
        first_response = self.client.post(
            f"/api/v1/organizer/events/{event.id}/organizers/",
            {"email": member.email},
            format="json",
        )
        self.assertEqual(first_response.status_code, status.HTTP_200_OK)

        delete_response = self.client.delete(
            f"/api/v1/organizer/events/{event.id}/organizers/",
            {"email": member.email},
            format="json",
        )
        self.assertEqual(delete_response.status_code, status.HTTP_200_OK)
        deleted_role = EventOrganizer.all_objects.get(event=event, user=member)
        self.assertIsNotNone(deleted_role.deleted_at)

        second_response = self.client.post(
            f"/api/v1/organizer/events/{event.id}/organizers/",
            {"email": member.email},
            format="json",
        )

        self.assertEqual(second_response.status_code, status.HTTP_200_OK)
        self.assertEqual(second_response.data["data"]["id"], str(deleted_role.id))
        self.assertEqual(
            EventOrganizer.all_objects.filter(event=event, user=member).count(),
            1,
        )
        restored_role = EventOrganizer.objects.get(event=event, user=member)
        self.assertIsNone(restored_role.deleted_at)
        self.assertEqual(
            restored_role.organizer_role,
            EventOrganizer.OrganizerRole.CO_HOST,
        )

    def test_add_event_organizer_by_owner_email_does_not_downgrade_owner(self):
        owner = User.objects.create_user(
            username="owner_email",
            email="owner@example.com",
            password="pass123",
            full_name="Owner Email",
        )
        event = Event.objects.create(
            category=self.category,
            created_by=owner,
            title="Owner Stays Owner Event",
            slug="owner-stays-owner-event",
            **self.valid_times,
        )
        owner_role = EventOrganizer.objects.create(
            event=event,
            user=owner,
            organizer_role=EventOrganizer.OrganizerRole.OWNER,
        )

        self.client.force_authenticate(user=owner)
        response = self.client.post(
            f"/api/v1/organizer/events/{event.id}/organizers/",
            {"email": owner.email},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        owner_role.refresh_from_db()
        self.assertEqual(
            owner_role.organizer_role,
            EventOrganizer.OrganizerRole.OWNER,
        )
        self.assertEqual(response.data["data"]["id"], str(owner_role.id))
        self.assertEqual(response.data["data"]["organizer_role"], "owner")

    def test_non_owner_cannot_add_event_organizer_by_email(self):
        member = User.objects.create_user(
            username="team_member_2",
            email="team2@example.com",
            password="pass123",
        )
        event = Event.objects.create(
            category=self.category,
            created_by=self.organizer,
            title="Owner Only Team Event",
            slug="owner-only-team-event",
            **self.valid_times,
        )
        EventOrganizer.objects.create(
            event=event,
            user=self.organizer,
            organizer_role=EventOrganizer.OrganizerRole.OWNER,
        )
        EventOrganizer.objects.create(
            event=event,
            user=self.other_organizer,
            organizer_role=EventOrganizer.OrganizerRole.CO_HOST,
        )

        self.client.force_authenticate(user=self.other_organizer)
        response = self.client.post(
            f"/api/v1/organizer/events/{event.id}/organizers/",
            {"email": member.email},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(
            EventOrganizer.objects.filter(event=event, user=member).exists()
        )

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

    def test_organizer_patch_stores_cover_image_key_and_returns_presigned_get_url(self):
        event = Event.objects.create(
            category=self.category,
            created_by=self.organizer,
            title="Image Event",
            slug="image-event-1",
            **self.valid_times,
        )
        s3_client = Mock()
        s3_client.generate_presigned_url.return_value = (
            "https://s3.test/events/image.jpg?signature=abc"
        )

        self.client.force_authenticate(user=self.organizer)
        with patch("apps.events.serializers.S3Client", return_value=s3_client):
            response = self.client.patch(
                f"/api/v1/organizer/events/{event.id}/",
                {"cover_image_key": "events/user-1/covers/image.jpg"},
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        event.refresh_from_db()
        self.assertEqual(event.cover_image_key, "events/user-1/covers/image.jpg")
        self.assertEqual(
            response.data["data"]["cover_image_url"],
            "https://s3.test/events/image.jpg?signature=abc",
        )
        s3_client.generate_presigned_url.assert_called_with(
            "events/user-1/covers/image.jpg",
            method="get_object",
            expires_in=3600,
        )

    @override_settings(
        AWS_S3_PRESIGNED_URL_EXPIRES=3600, AWS_S3_PRESIGNED_GET_URL_CACHE_TTL=300
    )
    def test_cover_image_presigned_get_url_is_cached_by_object_key(self):
        event = Event.objects.create(
            category=self.category,
            created_by=self.organizer,
            title="Cached Image Event",
            slug="cached-image-event",
            cover_image_key="events/user-1/covers/cached.jpg",
            **self.valid_times,
        )
        s3_client = Mock()
        s3_client.generate_presigned_url.return_value = (
            "https://s3.test/cached.jpg?signature=abc"
        )

        self.client.force_authenticate(user=self.organizer)
        with patch("apps.events.serializers.S3Client", return_value=s3_client):
            first_response = self.client.get(f"/api/v1/organizer/events/{event.id}/")
            second_response = self.client.get(f"/api/v1/organizer/events/{event.id}/")

        self.assertEqual(first_response.status_code, status.HTTP_200_OK)
        self.assertEqual(second_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            second_response.data["data"]["cover_image_url"],
            "https://s3.test/cached.jpg?signature=abc",
        )
        s3_client.generate_presigned_url.assert_called_once_with(
            "events/user-1/covers/cached.jpg",
            method="get_object",
            expires_in=3600,
        )

    @override_settings(
        AWS_S3_PRESIGNED_URL_EXPIRES=120, AWS_S3_PRESIGNED_GET_URL_CACHE_TTL=300
    )
    def test_cover_image_cache_timeout_stays_below_presigned_expiry(self):
        from apps.events.serializers import EventCoverImageUrlMixin

        self.assertEqual(EventCoverImageUrlMixin._cover_image_cache_timeout(120), 60)

    def test_organizer_patch_rejects_cover_image_url_as_storage_contract(self):
        event = Event.objects.create(
            category=self.category,
            created_by=self.organizer,
            title="Image Event",
            slug="image-event-url-reject",
            **self.valid_times,
        )
        self.client.force_authenticate(user=self.organizer)
        response = self.client.patch(
            f"/api/v1/organizer/events/{event.id}/",
            {"cover_image_key": "https://s3.test/events/image.jpg?signature=abc"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_organizer_can_patch_event_category_and_clear_room(self):
        new_category = EventCategory.objects.create(
            name="Conference",
            slug="conference",
            is_active=True,
        )
        campus = Campus.objects.create(name="Main Campus", code="MAIN")
        building = Building.objects.create(
            name="Main Building", code="MB", campus=campus
        )
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

    @override_settings(AWS_S3_PRESIGNED_URL_EXPIRES=900)
    def test_presigned_upload_url_response_returns_object_key_not_public_url(self):
        s3_client = Mock()
        s3_client.generate_presigned_url.return_value = (
            "https://s3.test/upload?signature=abc"
        )

        self.client.force_authenticate(user=self.organizer)
        with patch("apps.events.views.S3Client", return_value=s3_client):
            response = self.client.post(
                "/api/v1/organizer/events/presigned-url/",
                {"file_name": "cover.jpg", "content_type": "image/jpeg"},
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]
        self.assertTrue(
            data["object_key"].startswith(f"events/{self.organizer.id}/covers/")
        )
        self.assertEqual(
            data["presigned_upload_url"], "https://s3.test/upload?signature=abc"
        )
        self.assertEqual(data["presigned_url"], "https://s3.test/upload?signature=abc")
        self.assertNotIn("public_url", data)
        self.assertEqual(data["method"], "PUT")
        self.assertEqual(data["expires_in"], 900)

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

    def test_anonymous_user_can_retrieve_public_event_detail(self):
        campus = Campus.objects.create(name="Main Campus", code="MAIN")
        building = Building.objects.create(
            name="Main Building", code="MB", campus=campus
        )
        room = Room.objects.create(name="Auditorium", code="A1", building=building)
        event = Event.objects.create(
            category=self.category,
            room=room,
            created_by=self.organizer,
            title="Public Detail Event",
            slug="public-detail-event",
            description="Detail page content",
            visibility=Event.Visibility.PUBLIC,
            status=Event.Status.ACTIVE,
            **self.valid_times,
        )
        RegistrationFormField.objects.create(
            event=event,
            field_key="shirt_size",
            label="Shirt size",
            field_type="select",
            options_json=["S", "M", "L"],
            sort_order=1,
        )
        EventOrganizer.objects.create(
            event=event,
            user=self.organizer,
            organizer_role=EventOrganizer.OrganizerRole.OWNER,
        )

        response = self.client.get(f"/api/v1/events/{event.id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["title"], "Public Detail Event")
        self.assertEqual(response.data["data"]["room"]["code"], "A1")
        self.assertEqual(
            response.data["data"]["created_by"]["id"], str(self.organizer.id)
        )
        self.assertEqual(
            response.data["data"]["created_by"]["username"], self.organizer.username
        )
        self.assertEqual(
            response.data["data"]["created_by"]["full_name"], "Organizer User"
        )
        self.assertTrue(
            response.data["data"]["created_by"]["avatar_url"].startswith(
                "https://ui-avatars.com/api/"
            )
        )
        self.assertEqual(
            response.data["data"]["registration_fields"][0]["field_key"], "shirt_size"
        )
        self.assertEqual(response.data["data"]["user_event_relation"], "unregistered")
        self.assertEqual(
            response.data["data"]["organizers"][0]["user"]["id"],
            str(self.organizer.id),
        )
        self.assertTrue(
            response.data["data"]["organizers"][0]["user"]["avatar_url"].startswith(
                "https://ui-avatars.com/api/"
            )
        )

    def test_public_event_detail_returns_registered_user_relation(self):
        attendee = User.objects.create_user(username="attendee", password="pass123")
        event = Event.objects.create(
            category=self.category,
            created_by=self.organizer,
            title="Registered Relation Event",
            slug="registered-relation-event",
            visibility=Event.Visibility.PUBLIC,
            status=Event.Status.ACTIVE,
            **self.valid_times,
        )
        EventRegistration.objects.create(
            event=event,
            user=attendee,
            status=EventRegistration.RegistrationStatus.REGISTERED,
        )

        self.client.force_authenticate(user=attendee)
        response = self.client.get(f"/api/v1/events/{event.id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["user_event_relation"], "registered")

    def test_public_event_detail_returns_owner_user_relation(self):
        event = Event.objects.create(
            category=self.category,
            created_by=self.organizer,
            title="Owner Relation Event",
            slug="owner-relation-event",
            visibility=Event.Visibility.PUBLIC,
            status=Event.Status.ACTIVE,
            **self.valid_times,
        )

        self.client.force_authenticate(user=self.organizer)
        response = self.client.get(f"/api/v1/events/{event.id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["user_event_relation"], "owner")

    def test_public_event_detail_returns_cohost_user_relation(self):
        cohost = User.objects.create_user(username="cohost", password="pass123")
        event = Event.objects.create(
            category=self.category,
            created_by=self.organizer,
            title="Cohost Relation Event",
            slug="cohost-relation-event",
            visibility=Event.Visibility.PUBLIC,
            status=Event.Status.ACTIVE,
            **self.valid_times,
        )
        EventOrganizer.objects.create(
            event=event,
            user=cohost,
            organizer_role=EventOrganizer.OrganizerRole.CO_HOST,
        )

        self.client.force_authenticate(user=cohost)
        response = self.client.get(f"/api/v1/events/{event.id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["user_event_relation"], "cohost")

    def test_public_event_detail_hides_private_or_unpublished_events(self):
        draft_event = Event.objects.create(
            category=self.category,
            created_by=self.organizer,
            title="Draft Event",
            slug="draft-detail-event",
            visibility=Event.Visibility.PUBLIC,
            status=Event.Status.DRAFT,
            **self.valid_times,
        )
        private_event = Event.objects.create(
            category=self.category,
            created_by=self.organizer,
            title="Private Event",
            slug="private-detail-event",
            visibility=Event.Visibility.PRIVATE,
            status=Event.Status.ACTIVE,
            **self.valid_times,
        )

        draft_response = self.client.get(f"/api/v1/events/{draft_event.id}/")
        private_response = self.client.get(f"/api/v1/events/{private_event.id}/")

        self.assertEqual(draft_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(private_response.status_code, status.HTTP_404_NOT_FOUND)

    @override_settings(PUBLIC_WEB_BASE_URL="https://public.uevent.test")
    def test_authenticated_user_can_get_share_link_for_public_event(self):
        event = Event.objects.create(
            category=self.category,
            created_by=self.organizer,
            title="Shareable Event",
            slug="shareable-event",
            visibility=Event.Visibility.PUBLIC,
            status=Event.Status.ACTIVE,
            **self.valid_times,
        )
        attendee = User.objects.create_user(username="share_user", password="pass123")

        self.client.force_authenticate(user=attendee)
        response = self.client.get(f"/api/v1/events/{event.id}/share-link/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["event_id"], str(event.id))
        self.assertEqual(response.data["data"]["slug"], "shareable-event")
        self.assertEqual(
            response.data["data"]["share_url"],
            "https://public.uevent.test/events/share/shareable-event",
        )
        self.assertEqual(response.data["data"]["visibility"], Event.Visibility.PUBLIC)

    def test_share_link_requires_authentication(self):
        event = Event.objects.create(
            category=self.category,
            created_by=self.organizer,
            title="Auth Share Event",
            slug="auth-share-event",
            visibility=Event.Visibility.PUBLIC,
            status=Event.Status.ACTIVE,
            **self.valid_times,
        )

        response = self.client.get(f"/api/v1/events/{event.id}/share-link/")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_share_link_returns_forbidden_for_private_event(self):
        event = Event.objects.create(
            category=self.category,
            created_by=self.organizer,
            title="Private Share Event",
            slug="private-share-event",
            visibility=Event.Visibility.PRIVATE,
            status=Event.Status.ACTIVE,
            **self.valid_times,
        )
        attendee = User.objects.create_user(
            username="private_share_user", password="pass123"
        )

        self.client.force_authenticate(user=attendee)
        response = self.client.get(f"/api/v1/events/{event.id}/share-link/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_share_link_returns_not_found_for_soft_deleted_event(self):
        event = Event.objects.create(
            category=self.category,
            created_by=self.organizer,
            title="Deleted Share Event",
            slug="deleted-share-event",
            visibility=Event.Visibility.PUBLIC,
            status=Event.Status.ACTIVE,
            **self.valid_times,
        )
        attendee = User.objects.create_user(
            username="deleted_share_user", password="pass123"
        )
        event.delete()

        self.client.force_authenticate(user=attendee)
        response = self.client.get(f"/api/v1/events/{event.id}/share-link/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_share_link_returns_not_found_for_missing_event(self):
        attendee = User.objects.create_user(
            username="missing_share_user", password="pass123"
        )

        self.client.force_authenticate(user=attendee)
        response = self.client.get(f"/api/v1/events/{uuid.uuid4()}/share-link/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_anonymous_user_can_retrieve_public_event_detail_by_slug(self):
        event = Event.objects.create(
            category=self.category,
            created_by=self.organizer,
            title="Slug Landing Event",
            slug="slug-landing-event",
            visibility=Event.Visibility.PUBLIC,
            status=Event.Status.ACTIVE,
            **self.valid_times,
        )

        response = self.client.get("/api/v1/events/slug/slug-landing-event/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["id"], str(event.id))
        self.assertEqual(response.data["data"]["slug"], "slug-landing-event")

    def test_public_event_detail_by_slug_hides_private_event(self):
        Event.objects.create(
            category=self.category,
            created_by=self.organizer,
            title="Private Slug Event",
            slug="private-slug-event",
            visibility=Event.Visibility.PRIVATE,
            status=Event.Status.ACTIVE,
            **self.valid_times,
        )

        response = self.client.get("/api/v1/events/slug/private-slug-event/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_event_highlights_prioritizes_registered_events_regardless_status(
        self,
    ):
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
