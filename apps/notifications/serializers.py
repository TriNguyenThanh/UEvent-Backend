from rest_framework import serializers
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from apps.notifications.models import NotificationPreference


class NotificationInboxOutputSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    recipient_id = serializers.UUIDField()
    notification_id = serializers.UUIDField()
    event_id = serializers.UUIDField(allow_null=True)
    registration_id = serializers.UUIDField(allow_null=True)
    ticket_id = serializers.UUIDField(allow_null=True)
    question_id = serializers.UUIDField(allow_null=True)
    title = serializers.CharField()
    message = serializers.CharField()
    type = serializers.CharField()
    category = serializers.CharField()
    target = serializers.CharField()
    role_hint = serializers.CharField(allow_blank=True, allow_null=True)
    delivery_status = serializers.CharField()
    delivered_at = serializers.DateTimeField(allow_null=True)
    read_at = serializers.DateTimeField(allow_null=True)
    opened_at = serializers.DateTimeField(allow_null=True)
    action_label = serializers.CharField(allow_blank=True, allow_null=True)
    action_route = serializers.CharField(allow_blank=True, allow_null=True)
    created_at = serializers.DateTimeField()


class DeviceRegistrationInputSerializer(serializers.Serializer):
    fcm_token = serializers.CharField(
        max_length=512, required=True, allow_blank=False, trim_whitespace=True
    )
    device_name = serializers.CharField(
        max_length=120, required=False, allow_blank=True, trim_whitespace=True
    )


class DeviceUnregistrationInputSerializer(serializers.Serializer):
    fcm_token = serializers.CharField(
        max_length=512, required=True, allow_blank=False, trim_whitespace=True
    )


class NotificationPreferenceOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = [
            "id",
            "push_enabled",
            "event_reminders_enabled",
            "ticket_updates_enabled",
            "organizer_updates_enabled",
            "marketing_enabled",
            "quiet_hours_enabled",
            "quiet_hours_start",
            "quiet_hours_end",
            "timezone",
            "updated_at",
        ]


class NotificationPreferenceInputSerializer(serializers.Serializer):
    push_enabled = serializers.BooleanField(required=False)
    event_reminders_enabled = serializers.BooleanField(required=False)
    ticket_updates_enabled = serializers.BooleanField(required=False)
    organizer_updates_enabled = serializers.BooleanField(required=False)
    marketing_enabled = serializers.BooleanField(required=False)
    quiet_hours_enabled = serializers.BooleanField(required=False)
    quiet_hours_start = serializers.TimeField(required=False, allow_null=True)
    quiet_hours_end = serializers.TimeField(required=False, allow_null=True)
    timezone = serializers.CharField(
        max_length=64, required=False, allow_blank=False, trim_whitespace=True
    )

    def validate_timezone(self, value):
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise serializers.ValidationError("Múi giờ không hợp lệ.") from exc
        return value


class OrganizerNotificationInputSerializer(serializers.Serializer):
    title = serializers.CharField(
        max_length=160, required=True, allow_blank=False, trim_whitespace=True
    )
    message = serializers.CharField(
        max_length=2000, required=True, allow_blank=False, trim_whitespace=True
    )
    audience = serializers.ChoiceField(
        choices=[
            "registered",
            "checked_in",
            "waitlisted",
            "active",
            "all_participants",
        ],
        default="registered",
    )
    send_push = serializers.BooleanField(default=True)


class OrganizerNotificationOutputSerializer(serializers.Serializer):
    notification_id = serializers.UUIDField()
    recipient_count = serializers.IntegerField()
    queued_count = serializers.IntegerField()
