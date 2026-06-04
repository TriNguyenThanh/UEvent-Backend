from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.events.models import Event, EventCategory, EventOrganizer
from apps.interactions.models import (
    EventFeedback,
    EventQuestion,
    EventQuestionReply,
)
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
            f"/api/v1/events/{self.event.id}/feedbacks/",
            {
                "rating": 5,
                "content": "Great event",
                "is_anonymous": False,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(EventFeedback.objects.count(), 1)
        self.assertEqual(response.data["rating"], 5)

    def test_create_feedback_with_nested_event_endpoint_and_doc_aliases(self):
        response = self.client.post(
            f"/api/v1/events/{self.event.id}/feedbacks/",
            {
                "rating": 5,
                "comment": "Great event",
                "isAnonymous": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(EventFeedback.objects.count(), 1)
        self.assertEqual(response.data["content"], "Great event")
        self.assertTrue(response.data["is_anonymous"])

    def test_organizer_can_list_feedbacks_and_summary(self):
        EventFeedback.objects.create(event=self.event, user=self.user, rating=4, content="Good")
        EventOrganizer.objects.create(
            event=self.event,
            user=self.other_user,
            organizer_role=EventOrganizer.OrganizerRole.OWNER,
        )
        self.client.force_authenticate(self.other_user)

        list_response = self.client.get(f"/api/v1/events/{self.event.id}/feedbacks/")
        summary_response = self.client.get(f"/api/v1/events/{self.event.id}/feedbacks/summary/")

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(list_response.data["count"], 1)
        self.assertEqual(summary_response.status_code, status.HTTP_200_OK)
        self.assertEqual(summary_response.data["total"], 1)
        self.assertEqual(summary_response.data["rating_counts"]["4"], 1)

    def test_non_organizer_cannot_list_feedbacks(self):
        response = self.client.get(f"/api/v1/events/{self.event.id}/feedbacks/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_feedback_rejects_duplicate_for_same_event(self):
        EventFeedback.objects.create(
            event=self.event,
            user=self.user,
            rating=4,
            content="Existing feedback",
        )

        response = self.client.post(
            f"/api/v1/events/{self.event.id}/feedbacks/",
            {"rating": 5, "content": "Again"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(EventFeedback.objects.count(), 1)

    def test_question_crud_for_owner(self):
        create_response = self.client.post(
            f"/api/v1/events/{self.event.id}/questions/",
            {
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

    def test_create_question_with_nested_event_endpoint(self):
        response = self.client.post(
            f"/api/v1/events/{self.event.id}/questions/",
            {
                "question_text": "Will slides be shared?",
                "is_anonymous": False,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(EventQuestion.objects.count(), 1)
        self.assertEqual(response.data["event"]["id"], str(self.event.id))

    def test_public_questions_only_returns_visible_questions(self):
        visible = EventQuestion.objects.create(
            event=self.event,
            user=self.user,
            question_text="Visible question",
            moderation_status=EventQuestion.ModerationStatus.VISIBLE,
        )
        EventQuestion.objects.create(
            event=self.event,
            user=self.user,
            question_text="Hidden question",
            moderation_status=EventQuestion.ModerationStatus.HIDDEN,
        )

        response = self.client.get(f"/api/v1/events/{self.event.id}/questions/public/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], str(visible.id))

    def test_question_replies_are_saved_and_returned_with_public_questions(self):
        question = EventQuestion.objects.create(
            event=self.event,
            user=self.user,
            question_text="Can I ask a follow-up?",
        )

        reply_response = self.client.post(
            f"/api/v1/questions/{question.id}/replies/",
            {"content": "Yes, this is my follow-up."},
            format="json",
        )
        public_response = self.client.get(
            f"/api/v1/events/{self.event.id}/questions/public/"
        )

        self.assertEqual(reply_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(EventQuestionReply.objects.count(), 1)
        self.assertFalse(reply_response.data["is_organizer_reply"])
        self.assertEqual(public_response.status_code, status.HTTP_200_OK)
        replies = public_response.data["results"][0]["replies"]
        self.assertEqual(len(replies), 1)
        self.assertEqual(replies[0]["content"], "Yes, this is my follow-up.")

    def test_organizer_question_reply_is_marked_as_organizer_reply(self):
        question = EventQuestion.objects.create(
            event=self.event,
            user=self.user,
            question_text="Will there be Q&A?",
        )
        EventOrganizer.objects.create(
            event=self.event,
            user=self.other_user,
            organizer_role=EventOrganizer.OrganizerRole.OWNER,
        )
        self.client.force_authenticate(self.other_user)

        response = self.client.post(
            f"/api/v1/questions/{question.id}/replies/",
            {"content": "Yes, we will answer questions here."},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["is_organizer_reply"])

    def test_organizer_can_answer_pin_and_hide_question(self):
        question = EventQuestion.objects.create(
            event=self.event,
            user=self.user,
            question_text="Will there be Q&A?",
        )
        EventOrganizer.objects.create(
            event=self.event,
            user=self.other_user,
            organizer_role=EventOrganizer.OrganizerRole.OWNER,
        )
        self.client.force_authenticate(self.other_user)

        answer_response = self.client.patch(
            f"/api/v1/questions/{question.id}/answer/",
            {"answer_text": "Yes"},
            format="json",
        )
        pin_response = self.client.patch(f"/api/v1/questions/{question.id}/pin/")
        hide_response = self.client.patch(f"/api/v1/questions/{question.id}/hide/")

        self.assertEqual(answer_response.status_code, status.HTTP_200_OK)
        self.assertEqual(answer_response.data["answer_text"], "Yes")
        self.assertEqual(pin_response.status_code, status.HTTP_200_OK)
        self.assertTrue(pin_response.data["is_pinned"])
        self.assertEqual(hide_response.status_code, status.HTTP_200_OK)
        self.assertEqual(hide_response.data["moderation_status"], EventQuestion.ModerationStatus.HIDDEN)
