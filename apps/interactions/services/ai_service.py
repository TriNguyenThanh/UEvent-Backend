import hashlib
import json
import logging
from decimal import Decimal, InvalidOperation

import requests
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.interactions.models import (
    AIQuestionAnswerJob,
    EventAITopic,
    EventQuestionReply,
)
from apps.users.models import User

logger = logging.getLogger(__name__)


class DifyAIQAService:
    ALLOWED_CLASSIFICATIONS = set(AIQuestionAnswerJob.Classification.values)

    @classmethod
    def build_inputs(cls, question, ai_setting):
        event = question.event
        topics = EventAITopic.objects.filter(
            event=event,
            is_enabled=True,
        ).order_by("title", "created_at")
        topic_content = [
            {
                "title": topic.title,
                "description": topic.description,
                "keywords": topic.keywords,
                "reference_content": topic.reference_content,
            }
            for topic in topics
        ]
        timeline = {
            "start_at": event.start_at.isoformat() if event.start_at else None,
            "end_at": event.end_at.isoformat() if event.end_at else None,
            "registration_open_at": (
                event.registration_open_at.isoformat()
                if event.registration_open_at
                else None
            ),
            "registration_close_at": (
                event.registration_close_at.isoformat()
                if event.registration_close_at
                else None
            ),
        }
        return {
            "event_title": event.title,
            "event_description": event.description or "",
            "event_timeline": json.dumps(timeline, ensure_ascii=False),
            "question_text": question.question_text,
            "organizer_instructions": ai_setting.organizer_instructions or "",
            "event_topics": json.dumps(topic_content, ensure_ascii=False),
        }

    @classmethod
    def call_dify_workflow(cls, question, ai_setting, job):
        if not settings.DIFY_AI_QA_ENABLED:
            cls._mark_skipped(job, "Dify AI Q&A is disabled.")
            return
        if not settings.DIFY_API_KEY:
            cls._mark_failed(job, "configuration_error", "Dify API key is missing.")
            return

        inputs = cls.build_inputs(question, ai_setting)
        payload = {
            "inputs": inputs,
            "response_mode": "blocking",
            "user": str(question.user_id or f"anonymous-{question.id}"),
        }
        serialized_payload = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        job.request_payload_hash = hashlib.sha256(serialized_payload.encode()).hexdigest()
        job.save(update_fields=["request_payload_hash", "updated_at"])

        base_url = settings.DIFY_API_BASE_URL.rstrip("/")
        url = f"{base_url}/workflows/run"
        try:
            response = requests.post(
                url,
                json=payload,
                headers={
                    "Authorization": f"Bearer {settings.DIFY_API_KEY}",
                    "Content-Type": "application/json",
                },
                timeout=settings.DIFY_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            response_data = response.json()
            cls._store_response(job, ai_setting, response_data)
        except requests.Timeout:
            logger.warning("Dify timed out for AI answer job %s", job.id)
            cls._mark_failed(job, "timeout", "Dify API request timed out.")
        except requests.RequestException as exc:
            logger.warning("Dify request failed for AI answer job %s: %s", job.id, exc)
            cls._mark_failed(job, "http_error", str(exc))
        except (TypeError, ValueError, KeyError, InvalidOperation) as exc:
            logger.warning("Invalid Dify response for AI answer job %s: %s", job.id, exc)
            cls._mark_failed(job, "invalid_response", str(exc))

    @classmethod
    @transaction.atomic
    def _store_response(cls, job, ai_setting, response_data):
        workflow_data = response_data.get("data") or {}
        if workflow_data.get("status") not in (None, "succeeded"):
            raise ValueError(workflow_data.get("error") or "Dify workflow did not succeed.")
        outputs = workflow_data.get("outputs") or {}
        if isinstance(outputs, str):
            outputs = json.loads(outputs)
        if isinstance(outputs.get("result"), str):
            try:
                parsed_result = json.loads(outputs["result"])
            except json.JSONDecodeError:
                parsed_result = None
            if isinstance(parsed_result, dict):
                outputs = parsed_result

        classification = str(outputs["classification"]).strip().lower()
        if classification not in cls.ALLOWED_CLASSIFICATIONS:
            raise ValueError(f"Unsupported classification: {classification}")
        confidence = Decimal(str(outputs["confidence"]))
        if confidence < 0 or confidence > 1:
            raise ValueError("Confidence must be between 0 and 1.")
        answer = str(outputs.get("answer") or "").strip()
        reason = str(outputs.get("reason") or "").strip()
        now = timezone.now()

        job.classification = classification
        job.confidence = confidence
        job.reason = reason
        job.completed_at = now
        existing_reply_id = (job.dify_metadata or {}).get("reply_id")
        job.dify_metadata = {
            "task_id": response_data.get("task_id"),
            "workflow_run_id": response_data.get("workflow_run_id"),
            "elapsed_time": workflow_data.get("elapsed_time"),
            "total_tokens": workflow_data.get("total_tokens"),
        }
        job.result_payload_hash = hashlib.sha256(
            json.dumps(outputs, ensure_ascii=False, sort_keys=True).encode()
        ).hexdigest()

        if (
            classification == AIQuestionAnswerJob.Classification.ANSWERABLE
            and confidence >= ai_setting.min_confidence
            and answer
        ):
            job.status = AIQuestionAnswerJob.Status.COMPLETED
            job.draft_answer = ""
            reply = None
            if existing_reply_id:
                reply = EventQuestionReply.objects.filter(
                    pk=existing_reply_id,
                    question=job.question,
                ).first()
            if reply is None:
                print("Creating new EventQuestionReply for question:", job.question_id)
                user = User.objects.filter(pk=settings.DIFY_AI_ASSISTANT_USER_ID).first()
                if user is None:
                    raise ValueError("Dify AI Assistant user not found.")
                reply = EventQuestionReply.objects.create(
                    question=job.question,
                    user=user,
                    content=answer,
                    is_organizer_reply=True,
                )
            job.dify_metadata["reply_id"] = str(reply.id)
        else:
            job.status = AIQuestionAnswerJob.Status.SKIPPED
            job.draft_answer = ""
            if not job.reason:
                if classification != AIQuestionAnswerJob.Classification.ANSWERABLE:
                    job.reason = f"Classification is {classification}."
                elif confidence < ai_setting.min_confidence:
                    job.reason = "Confidence is below the configured threshold."
                else:
                    job.reason = "Dify returned an empty answer."
        job.error_code = ""
        job.error_message = ""
        job.save(
            update_fields=[
                "status",
                "classification",
                "confidence",
                "reason",
                "draft_answer",
                "error_code",
                "error_message",
                "result_payload_hash",
                "dify_metadata",
                "completed_at",
                "updated_at",
            ]
        )

    @staticmethod
    def _mark_skipped(job, reason):
        job.status = AIQuestionAnswerJob.Status.SKIPPED
        job.reason = reason
        job.completed_at = timezone.now()
        job.save(update_fields=["status", "reason", "completed_at", "updated_at"])

    @staticmethod
    def _mark_failed(job, error_code, error_message):
        job.status = AIQuestionAnswerJob.Status.FAILED
        job.error_code = error_code
        job.error_message = error_message
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
