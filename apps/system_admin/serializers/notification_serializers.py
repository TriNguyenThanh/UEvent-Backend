from django.utils import timezone
from rest_framework import serializers

from apps.notifications.models import Notification


class AdminNotificationActorSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    username = serializers.CharField()
    email = serializers.EmailField(allow_blank=True)
    full_name = serializers.CharField(allow_blank=True)


class AdminNotificationListOutputSerializer(serializers.ModelSerializer):
    created_by = AdminNotificationActorSerializer(read_only=True)
    recipient_count = serializers.IntegerField(read_only=True)
    sent_count = serializers.IntegerField(read_only=True)
    read_count = serializers.IntegerField(read_only=True)
    failed_count = serializers.IntegerField(read_only=True)
    open_rate = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            "id",
            "title",
            "message",
            "type",
            "audience_type",
            "status",
            "scheduled_at",
            "sent_at",
            "created_by",
            "recipient_count",
            "sent_count",
            "read_count",
            "failed_count",
            "open_rate",
            "created_at",
            "updated_at",
        ]

    def get_open_rate(self, obj):
        sent_count = getattr(obj, "sent_count", 0) or 0
        read_count = getattr(obj, "read_count", 0) or 0
        return round((read_count / sent_count) * 100, 1) if sent_count else 0


class AdminNotificationDetailOutputSerializer(AdminNotificationListOutputSerializer):
    performance = serializers.SerializerMethodField()

    class Meta(AdminNotificationListOutputSerializer.Meta):
        fields = [*AdminNotificationListOutputSerializer.Meta.fields, "performance"]

    def get_performance(self, obj):
        recipient_count = getattr(obj, "recipient_count", 0) or 0
        sent_count = getattr(obj, "sent_count", 0) or 0
        read_count = getattr(obj, "read_count", 0) or 0
        failed_count = getattr(obj, "failed_count", 0) or 0

        return {
            "recipient_count": recipient_count,
            "sent_count": sent_count,
            "read_count": read_count,
            "failed_count": failed_count,
            "open_rate": round((read_count / sent_count) * 100, 1) if sent_count else 0,
        }


class AdminNotificationInputSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255, required=True, allow_blank=False, trim_whitespace=True)
    message = serializers.CharField(required=True, allow_blank=False, trim_whitespace=True)
    type = serializers.ChoiceField(
        choices=Notification.NotificationType.choices,
        required=False,
        default=Notification.NotificationType.ANNOUNCEMENT,
    )
    audience_type = serializers.ChoiceField(
        choices=Notification.AudienceType.choices,
        required=False,
        default=Notification.AudienceType.ALL,
    )
    status = serializers.ChoiceField(
        choices=[
            Notification.NotificationStatus.DRAFT,
            Notification.NotificationStatus.SCHEDULED,
        ],
        required=False,
    )
    scheduled_at = serializers.DateTimeField(required=False, allow_null=True)
    event = serializers.UUIDField(required=False, allow_null=True)
    recipient_user_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=True,
    )

    def validate(self, attrs):
        status_value = attrs.get("status")
        scheduled_at = attrs.get("scheduled_at")

        if status_value == Notification.NotificationStatus.SCHEDULED and not scheduled_at:
            raise serializers.ValidationError({"scheduled_at": "Cần chọn thời điểm gửi khi lên lịch thông báo."})

        if scheduled_at and scheduled_at <= timezone.now():
            raise serializers.ValidationError({"scheduled_at": "Thời điểm gửi phải ở trong tương lai."})

        if status_value is None and not self.partial:
            attrs["status"] = (
                Notification.NotificationStatus.SCHEDULED
                if scheduled_at
                else Notification.NotificationStatus.DRAFT
            )

        return attrs

    def to_service_data(self):
        return dict(self.validated_data)


class AdminNotificationPublishInputSerializer(serializers.Serializer):
    recipient_user_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=True,
    )

    def to_service_data(self):
        return dict(self.validated_data)


class AdminNotificationStatisticsOutputSerializer(serializers.Serializer):
    total_sent = serializers.IntegerField()
    avg_open_rate = serializers.FloatField()
    scheduled = serializers.IntegerField()
    active_users = serializers.IntegerField()
