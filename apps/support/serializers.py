from rest_framework import serializers

from apps.support.models import (
    LegalDocument,
    SupportArticle,
    SupportCategory,
    SupportMessage,
    SupportTicket,
)


class LegalDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = LegalDocument
        fields = [
            "id",
            "document_type",
            "title",
            "version",
            "summary",
            "body",
            "locale",
            "published_at",
            "updated_at",
        ]


class SupportArticleSummarySerializer(serializers.ModelSerializer):
    category_slug = serializers.CharField(source="category.slug", read_only=True)

    class Meta:
        model = SupportArticle
        fields = [
            "id",
            "category_slug",
            "title",
            "slug",
            "summary",
            "locale",
            "published_at",
            "updated_at",
        ]


class SupportArticleDetailSerializer(SupportArticleSummarySerializer):
    class Meta(SupportArticleSummarySerializer.Meta):
        fields = [*SupportArticleSummarySerializer.Meta.fields, "body"]


class SupportCategoryHelpCenterSerializer(serializers.ModelSerializer):
    articles = serializers.SerializerMethodField()

    class Meta:
        model = SupportCategory
        fields = ["id", "name", "slug", "description", "sort_order", "articles"]

    def get_articles(self, obj):
        articles = getattr(obj, "published_articles", None)
        if articles is None:
            articles = obj.articles.filter(
                status=SupportArticle.ArticleStatus.PUBLISHED,
            )
        return SupportArticleSummarySerializer(articles, many=True).data


class SupportMessageSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = SupportMessage
        fields = [
            "id",
            "content",
            "is_staff",
            "author_name",
            "created_at",
            "updated_at",
        ]

    def get_author_name(self, obj):
        if obj.author_user:
            return obj.author_user.full_name or obj.author_user.username
        return "Hệ thống"


class SupportTicketSerializer(serializers.ModelSerializer):
    messages = SupportMessageSerializer(many=True, read_only=True)

    class Meta:
        model = SupportTicket
        fields = [
            "id",
            "subject",
            "description",
            "category",
            "priority",
            "status",
            "messages",
            "created_at",
            "updated_at",
        ]


class SupportTicketCreateSerializer(serializers.Serializer):
    subject = serializers.CharField(
        max_length=255,
        required=True,
        allow_blank=False,
        trim_whitespace=True,
    )
    description = serializers.CharField(
        required=True,
        allow_blank=False,
        trim_whitespace=True,
    )
    category = serializers.ChoiceField(
        choices=SupportTicket.Category.choices,
        required=False,
        default=SupportTicket.Category.OTHER,
    )

    def to_service_data(self):
        return dict(self.validated_data)


class SupportTicketMessageCreateSerializer(serializers.Serializer):
    content = serializers.CharField(
        required=True,
        allow_blank=False,
        trim_whitespace=True,
    )

    def to_service_data(self):
        return {"content": self.validated_data["content"]}
