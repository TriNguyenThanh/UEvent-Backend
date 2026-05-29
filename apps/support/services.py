from __future__ import annotations

from django.db import transaction
from django.db.models import Prefetch, Q, QuerySet
from django.utils import timezone

from common.exceptions import ValidationError
from common.response_codes import ResponseCode
from apps.support.models import (
    LegalDocument,
    SupportArticle,
    SupportCategory,
    SupportMessage,
    SupportTicket,
)


class HelpCenterService:
    @staticmethod
    def published_articles(*, locale: str = "vi") -> QuerySet[SupportArticle]:
        return (
            SupportArticle.objects.select_related("category")
            .filter(
                status=SupportArticle.ArticleStatus.PUBLISHED,
                locale=locale,
                category__is_active=True,
                category__deleted_at__isnull=True,
            )
            .order_by("category__sort_order", "sort_order", "title")
        )

    @staticmethod
    def list_categories(
        *,
        locale: str = "vi",
        category: str | None = None,
        search: str | None = None,
    ) -> QuerySet[SupportCategory]:
        articles = HelpCenterService.published_articles(locale=locale)

        if search:
            articles = articles.filter(
                Q(title__icontains=search)
                | Q(summary__icontains=search)
                | Q(body__icontains=search)
            )

        categories = SupportCategory.objects.filter(is_active=True)
        if category:
            categories = categories.filter(slug=category)

        return (
            categories.prefetch_related(
                Prefetch("articles", queryset=articles, to_attr="published_articles")
            )
            .filter(articles__in=articles)
            .distinct()
            .order_by("sort_order", "name")
        )

    @staticmethod
    def get_published_article(*, slug: str, locale: str = "vi") -> SupportArticle:
        return HelpCenterService.published_articles(locale=locale).get(slug=slug)

    @staticmethod
    def publish_article(article: SupportArticle) -> SupportArticle:
        article.status = SupportArticle.ArticleStatus.PUBLISHED
        if article.published_at is None:
            article.published_at = timezone.now()
        article.save(update_fields=["status", "published_at", "updated_at"])
        return article

    @staticmethod
    def archive_article(article: SupportArticle) -> SupportArticle:
        article.status = SupportArticle.ArticleStatus.ARCHIVED
        article.save(update_fields=["status", "updated_at"])
        return article


class LegalDocumentService:
    @staticmethod
    def get_latest_published(
        *,
        document_type: str,
        locale: str = "vi",
    ) -> LegalDocument:
        document = (
            LegalDocument.objects.filter(
                document_type=document_type,
                locale=locale,
                status=LegalDocument.DocumentStatus.PUBLISHED,
            )
            .order_by("-published_at", "-updated_at")
            .first()
        )
        if document is None:
            raise LegalDocument.DoesNotExist
        return document

    @staticmethod
    def publish(document: LegalDocument) -> LegalDocument:
        document.status = LegalDocument.DocumentStatus.PUBLISHED
        if document.published_at is None:
            document.published_at = timezone.now()
        document.save(update_fields=["status", "published_at", "updated_at"])
        return document

    @staticmethod
    def archive(document: LegalDocument) -> LegalDocument:
        document.status = LegalDocument.DocumentStatus.ARCHIVED
        document.save(update_fields=["status", "updated_at"])
        return document


class UserSupportTicketService:
    @staticmethod
    def list_tickets(*, user) -> QuerySet[SupportTicket]:
        return (
            SupportTicket.objects.filter(user=user)
            .prefetch_related("messages")
            .order_by("-updated_at", "-created_at")
        )

    @staticmethod
    def get_ticket(*, user, ticket_id) -> SupportTicket:
        return (
            SupportTicket.objects.filter(user=user)
            .prefetch_related("messages")
            .get(pk=ticket_id)
        )

    @staticmethod
    @transaction.atomic
    def create_ticket(*, user, data: dict) -> SupportTicket:
        ticket = SupportTicket.objects.create(
            user=user,
            subject=data["subject"],
            category=data.get("category") or SupportTicket.Category.OTHER,
            description=data["description"],
            priority=SupportTicket.TicketPriority.MEDIUM,
            status=SupportTicket.TicketStatus.OPEN,
        )
        SupportMessage.objects.create(
            ticket=ticket,
            author_user=user,
            content=data["description"],
            is_staff=False,
        )
        return UserSupportTicketService.get_ticket(user=user, ticket_id=ticket.id)

    @staticmethod
    @transaction.atomic
    def add_message(*, user, ticket: SupportTicket, content: str) -> SupportTicket:
        if ticket.status in {
            SupportTicket.TicketStatus.RESOLVED,
            SupportTicket.TicketStatus.CLOSED,
        }:
            raise ValidationError(
                {"ticket": "Yêu cầu hỗ trợ đã được xử lý nên không thể phản hồi thêm."},
                code=ResponseCode.VALIDATION_ERROR,
            )

        SupportMessage.objects.create(
            ticket=ticket,
            author_user=user,
            content=content,
            is_staff=False,
        )
        ticket.save(update_fields=["updated_at"])
        return UserSupportTicketService.get_ticket(user=user, ticket_id=ticket.id)
