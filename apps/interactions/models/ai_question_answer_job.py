from django.db import models

from common.models import BaseModel


class AIQuestionAnswerJob(BaseModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"
        SKIPPED = "skipped", "Skipped"
        FAILED = "failed", "Failed"
        CONFLICT = "conflict", "Conflict"

    class Classification(models.TextChoices):
        ANSWERABLE = "answerable", "Answerable"
        IRRELEVANT = "irrelevant", "Irrelevant"
        NEGATIVE = "negative", "Negative"
        GREETING = "greeting", "Greeting"
        NOT_ROOT = "not_root", "Not root"
        UNSAFE = "unsafe", "Unsafe"

    question = models.OneToOneField(
        "interactions.EventQuestion",
        on_delete=models.CASCADE,
        related_name="ai_answer_job",
    )
    idempotency_key = models.CharField(max_length=255, unique=True)
    request_payload_hash = models.CharField(max_length=64)
    result_payload_hash = models.CharField(max_length=64, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    classification = models.CharField(
        max_length=20,
        choices=Classification.choices,
        blank=True,
    )
    confidence = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        null=True,
        blank=True,
    )
    reason = models.TextField(blank=True)
    draft_answer = models.TextField(blank=True)
    error_code = models.CharField(max_length=100, blank=True)
    error_message = models.TextField(blank=True)
    broker_timestamp = models.DateTimeField(null=True, blank=True)
    dify_metadata = models.JSONField(default=dict, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta(BaseModel.Meta):
        db_table = "ai_question_answer_jobs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["question", "status"],
                name="ai_qa_job_question_status_idx",
            ),
            models.Index(
                fields=["status", "created_at"],
                name="ai_question_status_b48432_idx",
            ),
            models.Index(
                fields=["classification"],
                name="ai_question_classif_799cc7_idx",
            ),
            models.Index(
                fields=["broker_timestamp"],
                name="ai_question_broker__596479_idx",
            ),
        ]

    def __str__(self):
        return f"AI answer:{self.question_id}:{self.status}"
