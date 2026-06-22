import logging

from celery import shared_task
from django.utils import timezone

from apps.interactions.models import (
    AIQuestionAnswerJob,
    EventAIQASetting,
    EventQuestion,
)
from apps.interactions.services.ai_service import DifyAIQAService


logger = logging.getLogger(__name__)


@shared_task
def generate_ai_answer_for_question(question_id):
    try:
        question = EventQuestion.objects.select_related("event", "user").get(
            id=question_id
        )
        job = AIQuestionAnswerJob.objects.get(question=question)
    except (EventQuestion.DoesNotExist, AIQuestionAnswerJob.DoesNotExist):
        logger.warning("AI answer task has no question/job for %s", question_id)
        return

    if job.status != AIQuestionAnswerJob.Status.PENDING:
        return

    try:
        ai_setting = EventAIQASetting.objects.get(
            event=question.event,
            is_enabled=True,
        )
    except EventAIQASetting.DoesNotExist:
        job.status = AIQuestionAnswerJob.Status.SKIPPED
        job.reason = "AI Q&A is not enabled for this event."
        job.completed_at = timezone.now()
        job.save(update_fields=["status", "reason", "completed_at", "updated_at"])
        return

    try:
        DifyAIQAService.call_dify_workflow(question, ai_setting, job)
    except Exception as exc:
        logger.exception("Unexpected AI answer failure for job %s", job.id)
        job.status = AIQuestionAnswerJob.Status.FAILED
        job.error_code = "unexpected_error"
        job.error_message = str(exc)
        job.completed_at = timezone.now()
        job.save(
            update_fields=[
                "status",
                "error_code",
                "error_message",
                "completed_at",
                "updated_at",
            ]
        )
