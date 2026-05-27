from rest_framework import serializers
from django.utils import timezone

from apps.support.models import (
    LegalDocument,
    SupportArticle,
    SupportCategory,
    SupportMessage,
    SupportTicket,
)


class AdminSupportUserSummarySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    username = serializers.CharField()
    email = serializers.EmailField(allow_blank=True)
    full_name = serializers.CharField(allow_blank=True)


class AdminSupportMessageOutputSerializer(serializers.ModelSerializer):
    author = serializers.SerializerMethodField()

    class Meta:
        model = SupportMessage
        fields = ["id", "content", "is_staff", "author", "created_at", "updated_at"]

    def get_author(self, obj):
        if not obj.author_user:
            return None

        return {
            "id": obj.author_user.id,
            "username": obj.author_user.username,
            "email": obj.author_user.email,
            "full_name": obj.author_user.full_name,
        }


class AdminSupportTicketListOutputSerializer(serializers.ModelSerializer):
    user = AdminSupportUserSummarySerializer(read_only=True)
    assigned_to = AdminSupportUserSummarySerializer(read_only=True)
    latest_message = serializers.SerializerMethodField()
    message_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = SupportTicket
        fields = [
            "id",
            "subject",
            "description",
            "category",
            "priority",
            "status",
            "user",
            "assigned_to",
            "latest_message",
            "message_count",
            "created_at",
            "updated_at",
        ]

    def get_latest_message(self, obj):
        messages = getattr(obj, "prefetched_messages", None)
        message = (
            messages[-1] if messages else obj.messages.order_by("-created_at").first()
        )
        if not message:
            return None

        return AdminSupportMessageOutputSerializer(message).data


class AdminSupportTicketDetailOutputSerializer(AdminSupportTicketListOutputSerializer):
    messages = AdminSupportMessageOutputSerializer(many=True, read_only=True)
    user_context = serializers.SerializerMethodField()

    class Meta(AdminSupportTicketListOutputSerializer.Meta):
        fields = [
            *AdminSupportTicketListOutputSerializer.Meta.fields,
            "messages",
            "user_context",
        ]

    def get_user_context(self, obj):
        return {
            "tickets_count": getattr(obj, "user_ticket_count", 0),
            "events_count": getattr(obj, "user_event_count", 0),
            "channel": "Ứng dụng web",
            "related_event_name": "",
        }


class AdminSupportTicketUpdateInputSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=SupportTicket.TicketStatus.choices, required=False
    )
    priority = serializers.ChoiceField(
        choices=SupportTicket.TicketPriority.choices, required=False
    )
    assigned_to = serializers.UUIDField(required=False, allow_null=True)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("Cần có ít nhất một trường để cập nhật.")
        return attrs

    def to_service_data(self):
        return dict(self.validated_data)


class AdminSupportReplyInputSerializer(serializers.Serializer):
    content = serializers.CharField(
        required=True, allow_blank=False, trim_whitespace=True
    )

    def to_service_data(self):
        return {"content": self.validated_data["content"]}


class AdminSupportResolveInputSerializer(serializers.Serializer):
    note = serializers.CharField(required=False, allow_blank=True, trim_whitespace=True)

    def to_service_data(self):
        return {"note": self.validated_data.get("note", "")}


class AdminSupportEscalateInputSerializer(serializers.Serializer):
    reason = serializers.CharField(
        required=False, allow_blank=True, trim_whitespace=True
    )

    def to_service_data(self):
        return {"reason": self.validated_data.get("reason", "")}


class AdminSupportStatisticsOutputSerializer(serializers.Serializer):
    open_tickets = serializers.IntegerField()
    in_progress = serializers.IntegerField()
    resolved_today = serializers.IntegerField()
    avg_response_minutes = serializers.FloatField()


class AdminSupportCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportCategory
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "sort_order",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class AdminSupportArticleSerializer(serializers.ModelSerializer):
    category = AdminSupportCategorySerializer(read_only=True)
    category_id = serializers.UUIDField(write_only=True, required=True)

    class Meta:
        model = SupportArticle
        fields = [
            "id",
            "category",
            "category_id",
            "title",
            "slug",
            "summary",
            "body",
            "locale",
            "status",
            "sort_order",
            "published_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "category",
            "published_at",
            "created_at",
            "updated_at",
        ]

    def validate_category_id(self, value):
        if not SupportCategory.objects.filter(pk=value).exists():
            raise serializers.ValidationError("Danh mục hỗ trợ không tồn tại.")
        return value

    def create(self, validated_data):
        category_id = validated_data.pop("category_id")
        if validated_data.get(
            "status"
        ) == SupportArticle.ArticleStatus.PUBLISHED and not validated_data.get(
            "published_at"
        ):
            validated_data["published_at"] = timezone.now()
        return SupportArticle.objects.create(category_id=category_id, **validated_data)

    def update(self, instance, validated_data):
        category_id = validated_data.pop("category_id", None)
        if category_id is not None:
            instance.category_id = category_id

        for field, value in validated_data.items():
            setattr(instance, field, value)
        if (
            instance.status == SupportArticle.ArticleStatus.PUBLISHED
            and instance.published_at is None
        ):
            instance.published_at = timezone.now()
        instance.save()
        return instance


class AdminLegalDocumentSerializer(serializers.ModelSerializer):
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
            "status",
            "published_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "published_at", "created_at", "updated_at"]

    def create(self, validated_data):
        if validated_data.get(
            "status"
        ) == LegalDocument.DocumentStatus.PUBLISHED and not validated_data.get(
            "published_at"
        ):
            validated_data["published_at"] = timezone.now()
        return LegalDocument.objects.create(**validated_data)

    def update(self, instance, validated_data):
        for field, value in validated_data.items():
            setattr(instance, field, value)
        if (
            instance.status == LegalDocument.DocumentStatus.PUBLISHED
            and instance.published_at is None
        ):
            instance.published_at = timezone.now()
        instance.save()
        return instance
