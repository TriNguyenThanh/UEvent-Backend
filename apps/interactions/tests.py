from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.events.models import Event, EventCategory
from apps.interactions.models import EventFeedback, EventQuestion
from apps.registrations.models import EventRegistration
from apps.users.models import User


class InteractionApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="attendee",
            email="attendee@example.com",
            password="testpass123",
        )
        self.other_user = User.objects.create_user(
            username="other",
            email="other@example.com",
            password="testpass123",
        )
        self.category = EventCategory.objects.create(name="Workshop", slug="workshop")
        now = timezone.now()
        self.event = Event.objects.create(
            category=self.category,
            created_by=self.other_user,
            title="Django Workshop",
            slug="django-workshop",
            status=Event.Status.FINISHED,
            start_at=now - timedelta(days=2),
            end_at=now - timedelta(days=1),
        )
        EventRegistration.objects.create(
            event=self.event,
            user=self.user,
            status=EventRegistration.RegistrationStatus.REGISTERED,
        )
        self.client.force_authenticate(self.user)

    def test_create_feedback_for_finished_registered_event(self):
        response = self.client.post(
            reverse("feedback-list-create"),
            {
                "event_id": str(self.event.id),
                "rating": 5,
                "content": "Great event",
                "is_anonymous": False,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(EventFeedback.objects.count(), 1)
        self.assertEqual(response.data["rating"], 5)

    def test_create_feedback_rejects_duplicate_for_same_event(self):
        EventFeedback.objects.create(
            event=self.event,
            user=self.user,
            rating=4,
            content="Existing feedback",
        )

        response = self.client.post(
            reverse("feedback-list-create"),
            {"event_id": str(self.event.id), "rating": 5, "content": "Again"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(EventFeedback.objects.count(), 1)

    def test_question_crud_for_owner(self):
        create_response = self.client.post(
            reverse("question-list-create"),
            {
                "event_id": str(self.event.id),
                "question_text": "Will slides be shared?",
                "is_anonymous": True,
            },
            format="json",
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

        question_id = create_response.data["id"]
        patch_response = self.client.patch(
            reverse("question-detail", kwargs={"pk": question_id}),
            {"question_text": "Will slides be shared after the event?"},
            format="json",
        )
        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            patch_response.data["question_text"],
            "Will slides be shared after the event?",
        )

        delete_response = self.client.delete(
            reverse("question-detail", kwargs={"pk": question_id})
        )
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(EventQuestion.objects.count(), 0)
        self.assertEqual(EventQuestion.all_objects.count(), 1)
