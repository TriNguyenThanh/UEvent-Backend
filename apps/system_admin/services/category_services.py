from django.db import transaction
from django.db.models import Count, QuerySet
from django.utils.text import slugify

from apps.events.models import Event, EventCategory
from common.exceptions import NotFoundError, ValidationError

from .audit_service import AdminAuditService


class AdminCategoryService:
    @staticmethod
    def _categories_with_counts() -> QuerySet[EventCategory]:
        return EventCategory.objects.annotate(event_count=Count("events", distinct=True))

    @staticmethod
    def _log_audit(*, action, actor, category, reason="", metadata=None):
        AdminAuditService.log_action(
            action=action,
            actor=actor,
            target_type="events.EventCategory",
            target_id=str(category.pk),
            reason=reason,
            metadata=metadata,
        )

    @staticmethod
    def list_categories() -> QuerySet[EventCategory]:
        return AdminCategoryService._categories_with_counts()

    @staticmethod
    def get_category(category_id) -> EventCategory:
        try:
            return AdminCategoryService._categories_with_counts().get(pk=category_id)
        except EventCategory.DoesNotExist as exc:
            raise NotFoundError(f"Category with ID {category_id} does not exist.") from exc

    @staticmethod
    def get_category_statistics() -> dict:
        categories = AdminCategoryService._categories_with_counts()
        popular = categories.order_by("-event_count", "name").first()

        return {
            "total_categories": categories.count(),
            "active_categories": categories.filter(is_active=True).count(),
            "total_events": Event.objects.count(),
            "popular_category": {
                "id": popular.id,
                "name": popular.name,
                "slug": popular.slug,
                "event_count": popular.event_count,
            } if popular else None,
        }

    @staticmethod
    def _build_unique_slug(name: str, requested_slug: str = "") -> str:
        base_slug = slugify(requested_slug or name)
        if not base_slug:
            raise ValidationError("Slug danh mục không hợp lệ.")

        slug = base_slug[:140]
        suffix = 1
        while EventCategory.all_objects.filter(slug=slug).exists():
            suffix += 1
            suffix_text = f"-{suffix}"
            slug = f"{base_slug[:140 - len(suffix_text)]}{suffix_text}"
        return slug

    @staticmethod
    @transaction.atomic
    def create_category(*, actor, data: dict) -> EventCategory:
        payload = dict(data)
        payload["slug"] = AdminCategoryService._build_unique_slug(
            payload["name"],
            payload.get("slug") or "",
        )

        category = EventCategory.objects.create(**payload)
        AdminCategoryService._log_audit(
            action="create_category",
            actor=actor,
            category=category,
            metadata={"created_fields": list(payload.keys())},
        )
        return AdminCategoryService.get_category(category.pk)

    @staticmethod
    @transaction.atomic
    def update_category(*, actor, category_id, data: dict) -> EventCategory:
        category = AdminCategoryService.get_category(category_id)

        for field, value in data.items():
            setattr(category, field, value)

        if data:
            category.save(update_fields=[*data.keys(), "updated_at"])
            AdminCategoryService._log_audit(
                action="update_category",
                actor=actor,
                category=category,
                metadata={"updated_fields": list(data.keys())},
            )

        return AdminCategoryService.get_category(category_id)

    @staticmethod
    @transaction.atomic
    def delete_category(*, actor, category_id, reason: str = "") -> None:
        category = AdminCategoryService.get_category(category_id)
        event_count = Event.objects.filter(category=category).count()

        if event_count > 0:
            category.is_active = False
            category.save(update_fields=["is_active", "updated_at"])
            action = "deactivate_category"
            metadata = {"event_count": event_count, "strategy": "set_is_active_false"}
        else:
            category.delete()
            action = "delete_category"
            metadata = {"event_count": 0, "strategy": "soft_delete"}

        AdminCategoryService._log_audit(
            action=action,
            actor=actor,
            category=category,
            reason=reason,
            metadata=metadata,
        )
