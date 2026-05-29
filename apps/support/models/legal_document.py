from django.db import models

from common.models import BaseModel


class LegalDocument(BaseModel):
    class DocumentType(models.TextChoices):
        PRIVACY_POLICY = "privacy_policy", "Privacy Policy"
        TERMS_OF_SERVICE = "terms_of_service", "Terms of Service"

    class DocumentStatus(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        ARCHIVED = "archived", "Archived"

    document_type = models.CharField(max_length=40, choices=DocumentType.choices)
    title = models.CharField(max_length=180)
    version = models.CharField(max_length=60)
    summary = models.TextField(blank=True)
    body = models.TextField()
    locale = models.CharField(max_length=12, default="vi")
    status = models.CharField(
        max_length=20,
        choices=DocumentStatus.choices,
        default=DocumentStatus.DRAFT,
    )
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta(BaseModel.Meta):
        db_table = "support_legal_documents"
        ordering = ["document_type", "locale", "-published_at", "-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["document_type", "version", "locale"],
                name="uniq_legal_document_type_version_locale",
            ),
        ]
        indexes = [
            models.Index(fields=["document_type", "locale", "status"]),
            models.Index(fields=["status", "-published_at"]),
        ]

    def __str__(self):
        return f"{self.document_type}:{self.version}:{self.locale}"
