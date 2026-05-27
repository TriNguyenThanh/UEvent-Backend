from django.contrib import admin

from apps.support.models import (
    LegalDocument,
    SupportArticle,
    SupportCategory,
    SupportMessage,
    SupportTicket,
)


@admin.register(SupportCategory)
class SupportCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "sort_order", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name", "slug", "description")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("sort_order", "name")


@admin.register(SupportArticle)
class SupportArticleAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "category",
        "locale",
        "status",
        "sort_order",
        "published_at",
    )
    list_filter = ("status", "locale", "category")
    search_fields = ("title", "slug", "summary", "body")
    prepopulated_fields = {"slug": ("title",)}
    ordering = ("category__sort_order", "sort_order", "title")


@admin.register(LegalDocument)
class LegalDocumentAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "document_type",
        "version",
        "locale",
        "status",
        "published_at",
    )
    list_filter = ("document_type", "status", "locale")
    search_fields = ("title", "version", "summary", "body")
    ordering = ("document_type", "locale", "-published_at", "-updated_at")


admin.site.register(SupportTicket)
admin.site.register(SupportMessage)
