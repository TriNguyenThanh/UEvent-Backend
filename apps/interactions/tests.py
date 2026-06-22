from datetime import timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

import requests
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.events.models import Event, EventCategory, EventOrganizer
from apps.interactions.models import (
    AIQuestionAnswerJob,
    EventAIQASetting,
    # EventFeedback,
    EventQuestion,
    EventQuestionReply,
)
from apps.interactions.services.ai_service import DifyAIQAService
from apps.interactions.tasks import generate_ai_answer_for_question
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

    def create_ai_setting(self, **overrides):
        defaults = {
            "event": self.event,
            "is_enabled": True,
            "organizer_instructions": "Only answer from event context.",
            "min_confidence": Decimal("0.700"),
        }
        defaults.update(overrides)
        return EventAIQASetting.objects.create(**defaults)

    def create_ai_job(self, question, **overrides):
        defaults = {
            "question": question,
            "idempotency_key": f"event-question:{question.id}",
            "request_payload_hash": "0" * 64,
        }
        defaults.update(overrides)
        return AIQuestionAnswerJob.objects.create(**defaults)

    @override_settings(DIFY_AI_QA_ENABLED=False)
    def test_create_question_succeeds_when_dify_is_disabled(self):
        response = self.client.post(
            f"/api/v1/events/{self.event.id}/questions/",
            {"question_text": "Is lunch included?"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        question = EventQuestion.objects.get(id=response.data["id"])
        self.assertTrue(AIQuestionAnswerJob.objects.filter(question=question).exists())

    @patch("apps.interactions.tasks.generate_ai_answer_for_question.delay")
    def test_question_enqueues_ai_task_after_commit(self, mock_delay):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                f"/api/v1/events/{self.event.id}/questions/",
                {"question_text": "Where is the venue?"},
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        mock_delay.assert_called_once_with(response.data["id"])

    @patch(
        "apps.interactions.tasks.generate_ai_answer_for_question.delay",
        side_effect=RuntimeError("broker unavailable"),
    )
    def test_question_creation_survives_enqueue_failure(self, _mock_delay):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                f"/api/v1/events/{self.event.id}/questions/",
                {"question_text": "Will this still be saved?"},
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        job = AIQuestionAnswerJob.objects.get(question_id=response.data["id"])
        self.assertEqual(job.status, AIQuestionAnswerJob.Status.FAILED)
        self.assertEqual(job.error_code, "enqueue_error")

    @override_settings(DIFY_AI_QA_ENABLED=False)
    def test_disabled_dify_task_marks_job_skipped(self):
        question = EventQuestion.objects.create(
            event=self.event,
            user=self.user,
            question_text="Is this enabled?",
        )
        self.create_ai_setting()
        job = self.create_ai_job(question)

        generate_ai_answer_for_question(str(question.id))

        job.refresh_from_db()
        self.assertEqual(job.status, AIQuestionAnswerJob.Status.SKIPPED)

    @override_settings(
        DIFY_AI_QA_ENABLED=True,
        DIFY_API_BASE_URL="https://api.dify.test/v1",
        DIFY_API_KEY="test-key",
        DIFY_TIMEOUT_SECONDS=5,
    )
    @patch("apps.interactions.services.ai_service.requests.post")
    def test_dify_success_without_workflow_id_stores_draft(self, mock_post):
        question = EventQuestion.objects.create(
            event=self.event,
            user=self.user,
            question_text="Will slides be shared?",
        )
        ai_setting = self.create_ai_setting()
        job = self.create_ai_job(question)
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "task_id": "task-1",
            "workflow_run_id": "run-1",
            "data": {
                "status": "succeeded",
                "outputs": {
                    "classification": "answerable",
                    "confidence": 0.91,
                    "answer": "Yes, after the event.",
                    "reason": "Covered by organizer instructions.",
                },
            },
        }
        mock_post.return_value = response

        DifyAIQAService.call_dify_workflow(question, ai_setting, job)

        job.refresh_from_db()
        self.assertEqual(job.status, AIQuestionAnswerJob.Status.COMPLETED)
        self.assertEqual(job.draft_answer, "Yes, after the event.")
        self.assertFalse(EventQuestionReply.objects.filter(question=question).exists())
        self.assertEqual(
            mock_post.call_args.args[0],
            "https://api.dify.test/v1/workflows/run",
        )

    @override_settings(
        DIFY_AI_QA_ENABLED=True,
        DIFY_API_KEY="test-key",
    )
    @patch("apps.interactions.services.ai_service.requests.post")
    def test_dify_irrelevant_result_is_skipped(self, mock_post):
        question = EventQuestion.objects.create(
            event=self.event,
            user=self.user,
            question_text="Hello",
        )
        ai_setting = self.create_ai_setting()
        job = self.create_ai_job(question)
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "data": {
                "status": "succeeded",
                "outputs": {
                    "classification": "greeting",
                    "confidence": 0.99,
                    "answer": "Hello!",
                    "reason": "Not an event question.",
                },
            }
        }
        mock_post.return_value = response

        DifyAIQAService.call_dify_workflow(question, ai_setting, job)

        job.refresh_from_db()
        self.assertEqual(job.status, AIQuestionAnswerJob.Status.SKIPPED)
        self.assertEqual(job.draft_answer, "")

    @override_settings(
        DIFY_AI_QA_ENABLED=True,
        DIFY_API_KEY="test-key",
    )
    @patch(
        "apps.interactions.services.ai_service.requests.post",
        side_effect=requests.Timeout,
    )
    def test_dify_timeout_marks_job_failed(self, _mock_post):
        question = EventQuestion.objects.create(
            event=self.event,
            user=self.user,
            question_text="Will slides be shared?",
        )
        ai_setting = self.create_ai_setting()
        job = self.create_ai_job(question)

        DifyAIQAService.call_dify_workflow(question, ai_setting, job)

        job.refresh_from_db()
        self.assertEqual(job.status, AIQuestionAnswerJob.Status.FAILED)
        self.assertEqual(job.error_code, "timeout")
        self.assertTrue(EventQuestion.objects.filter(pk=question.pk).exists())

    @override_settings(
        DIFY_AI_QA_ENABLED=True,
        DIFY_API_KEY="test-key",
    )
    @patch(
        "apps.interactions.services.ai_service.requests.post",
        side_effect=requests.ConnectionError("Dify unavailable"),
    )
    def test_dify_http_error_marks_job_failed(self, _mock_post):
        question = EventQuestion.objects.create(
            event=self.event,
            user=self.user,
            question_text="Where is the venue?",
        )
        ai_setting = self.create_ai_setting()
        job = self.create_ai_job(question)

        DifyAIQAService.call_dify_workflow(question, ai_setting, job)

        job.refresh_from_db()
        self.assertEqual(job.status, AIQuestionAnswerJob.Status.FAILED)
        self.assertEqual(job.error_code, "http_error")

    def test_ai_draft_is_visible_only_in_organizer_question_api(self):
        question = EventQuestion.objects.create(
            event=self.event,
            user=self.user,
            question_text="Will slides be shared?",
        )
        self.create_ai_job(
            question,
            status=AIQuestionAnswerJob.Status.COMPLETED,
            classification=AIQuestionAnswerJob.Classification.ANSWERABLE,
            confidence=Decimal("0.9000"),
            draft_answer="Organizer-only draft",
        )

        public_response = self.client.get(
            f"/api/v1/events/{self.event.id}/questions/public/"
        )
        self.client.force_authenticate(self.other_user)
        organizer_response = self.client.get(
            f"/api/v1/events/{self.event.id}/questions/"
        )

        self.assertNotIn("ai_answer_job", public_response.data["results"][0])
        organizer_question = organizer_response.data["results"][0]
        self.assertEqual(
            organizer_question["ai_answer_job"]["draft_answer"],
            "Organizer-only draft",
        )

    def test_only_organizer_can_apply_completed_ai_draft(self):
        question = EventQuestion.objects.create(
            event=self.event,
            user=self.user,
            question_text="Will slides be shared?",
        )
        self.create_ai_job(
            question,
            status=AIQuestionAnswerJob.Status.COMPLETED,
            classification=AIQuestionAnswerJob.Classification.ANSWERABLE,
            confidence=Decimal("0.9000"),
            draft_answer="Yes, after the event.",
        )
        url = f"/api/v1/questions/{question.id}/ai-answer/apply/"

        forbidden_response = self.client.post(url, format="json")
        self.client.force_authenticate(self.other_user)
        applied_response = self.client.post(url, format="json")

        self.assertEqual(forbidden_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(applied_response.status_code, status.HTTP_201_CREATED)
        reply = EventQuestionReply.objects.get(question=question)
        self.assertEqual(reply.content, "Yes, after the event.")
        self.assertTrue(reply.is_organizer_reply)
