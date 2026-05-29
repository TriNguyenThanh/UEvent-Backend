from django.db import models

from common.models import BaseModel


class SupportArticle(BaseModel):
    class ArticleStatus(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        ARCHIVED = "archived", "Archived"

    category = models.ForeignKey(
        "support.SupportCategory",
        on_delete=models.PROTECT,
        related_name="articles",
    )
    title = models.CharField(max_length=180)
    slug = models.SlugField(max_length=200)
    summary = models.TextField(blank=True)
    body = models.TextField()
    locale = models.CharField(max_length=12, default="vi")
    status = models.CharField(
        max_length=20,
        choices=ArticleStatus.choices,
        default=ArticleStatus.DRAFT,
    )
    sort_order = models.PositiveIntegerField(default=0)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta(BaseModel.Meta):
        db_table = "support_articles"
        ordering = ["category__sort_order", "sort_order", "title"]
        constraints = [
            models.UniqueConstraint(
                fields=["slug", "locale"],
                name="uniq_support_article_slug_locale",
            ),
        ]
        indexes = [
            models.Index(fields=["status", "locale", "sort_order"]),
            models.Index(fields=["category", "status"]),
            models.Index(fields=["slug", "locale"]),
        ]

    def __str__(self):
        return self.title
