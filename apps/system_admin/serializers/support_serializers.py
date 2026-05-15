from rest_framework import serializers

from apps.support.models import SupportMessage, SupportTicket


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
        message = messages[-1] if messages else obj.messages.order_by("-created_at").first()
        if not message:
            return None

        return AdminSupportMessageOutputSerializer(message).data


class AdminSupportTicketDetailOutputSerializer(AdminSupportTicketListOutputSerializer):
    messages = AdminSupportMessageOutputSerializer(many=True, read_only=True)
    user_context = serializers.SerializerMethodField()

    class Meta(AdminSupportTicketListOutputSerializer.Meta):
        fields = [*AdminSupportTicketListOutputSerializer.Meta.fields, "messages", "user_context"]

    def get_user_context(self, obj):
        return {
            "tickets_count": getattr(obj, "user_ticket_count", 0),
            "events_count": getattr(obj, "user_event_count", 0),
            "channel": "Ứng dụng web",
            "related_event_name": "",
        }


class AdminSupportTicketUpdateInputSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=SupportTicket.TicketStatus.choices, required=False)
    priority = serializers.ChoiceField(choices=SupportTicket.TicketPriority.choices, required=False)
    assigned_to = serializers.UUIDField(required=False, allow_null=True)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("Cần có ít nhất một trường để cập nhật.")
        return attrs

    def to_service_data(self):
        return dict(self.validated_data)


class AdminSupportReplyInputSerializer(serializers.Serializer):
    content = serializers.CharField(required=True, allow_blank=False, trim_whitespace=True)

    def to_service_data(self):
        return {"content": self.validated_data["content"]}


class AdminSupportResolveInputSerializer(serializers.Serializer):
    note = serializers.CharField(required=False, allow_blank=True, trim_whitespace=True)

    def to_service_data(self):
        return {"note": self.validated_data.get("note", "")}


class AdminSupportEscalateInputSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, trim_whitespace=True)

    def to_service_data(self):
        return {"reason": self.validated_data.get("reason", "")}


class AdminSupportStatisticsOutputSerializer(serializers.Serializer):
    open_tickets = serializers.IntegerField()
    in_progress = serializers.IntegerField()
    resolved_today = serializers.IntegerField()
    avg_response_minutes = serializers.FloatField()
