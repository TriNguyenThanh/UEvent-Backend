from rest_framework import serializers

from apps.events.models import Event, EventCategory
from apps.events.serializers import EventCoverImageUrlMixin
from apps.moderation.models import ModerationLog
from apps.users.models import User


class AdminEventCategorySummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = EventCategory
        fields = ["id", "name", "slug", "color", "icon"]


class AdminEventUserSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "full_name"]


class AdminEventRoomSummarySerializer(serializers.Serializer):
    id = serializers.UUIDField(allow_null=True)
    name = serializers.CharField(allow_blank=True)
    code = serializers.CharField(allow_blank=True)
    building_name = serializers.CharField(allow_blank=True)
    campus_name = serializers.CharField(allow_blank=True)


class AdminModerationLogOutputSerializer(serializers.ModelSerializer):
    admin_user = AdminEventUserSummarySerializer(read_only=True)

    class Meta:
        model = ModerationLog
        fields = ["id", "admin_user", "report_type", "action", "reason", "created_at"]


class AdminEventListOutputSerializer(EventCoverImageUrlMixin, serializers.ModelSerializer):
    category = AdminEventCategorySummarySerializer(read_only=True)
    created_by = AdminEventUserSummarySerializer(read_only=True)
    room = serializers.SerializerMethodField()
    latest_report_type = serializers.SerializerMethodField()
    latest_moderation_reason = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = [
            "id",
            "title",
            "slug",
            "description",
            "visibility",
            "status",
            "category",
            "created_by",
            "room",
            "registration_open_at",
            "registration_close_at",
            "cancellation_deadline_at",
            "start_at",
            "end_at",
            "max_capacity",
            "location_snapshot",
            "cover_image_url",
            "deep_link",
            "latest_report_type",
            "latest_moderation_reason",
            "created_at",
            "updated_at",
        ]

    def get_room(self, obj):
        room = obj.room
        if room is None:
            return None

        building = getattr(room, "building", None)
        campus = getattr(building, "campus", None) if building is not None else None
        return {
            "id": room.id,
            "name": room.name,
            "code": room.code,
            "building_name": getattr(building, "name", ""),
            "campus_name": getattr(campus, "name", ""),
        }

    def _latest_moderation_log(self, obj):
        logs = list(getattr(obj, "prefetched_moderation_logs", []))
        if logs:
            return logs[0]
        return obj.moderation_logs.first()

    def get_latest_report_type(self, obj):
        log = self._latest_moderation_log(obj)
        return log.report_type if log and log.report_type else None

    def get_latest_moderation_reason(self, obj):
        log = self._latest_moderation_log(obj)
        return log.reason if log and log.reason else ""


class AdminEventDetailOutputSerializer(AdminEventListOutputSerializer):
    moderation_logs = AdminModerationLogOutputSerializer(many=True, read_only=True)

    class Meta(AdminEventListOutputSerializer.Meta):
        fields = [*AdminEventListOutputSerializer.Meta.fields, "moderation_logs"]


class AdminEventStatusInputSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=[
            Event.Status.APPROVED,
            Event.Status.REJECTED,
            Event.Status.CANCELLED,
            Event.Status.ARCHIVED,
            Event.Status.ACTIVE,
        ]
    )
    reason = serializers.CharField(required=False, allow_blank=True, default="")

    def to_service_data(self):
        return dict(self.validated_data)


class EventStatusCountSerializer(serializers.Serializer):
    status = serializers.CharField()
    count = serializers.IntegerField()


class EventCategoryCountSerializer(serializers.Serializer):
    category__id = serializers.UUIDField()
    category__name = serializers.CharField()
    count = serializers.IntegerField()


class AdminEventStatisticsOutputSerializer(serializers.Serializer):
    total_events = serializers.IntegerField()
    pending_approval = serializers.IntegerField()
    approved_today = serializers.IntegerField()
    reported_events = serializers.IntegerField()
    by_status = EventStatusCountSerializer(many=True)
    by_category = EventCategoryCountSerializer(many=True)


class AdminEventModerationPulseSerializer(serializers.Serializer):
    avg_response_hours = serializers.FloatField()
    queue_size = serializers.IntegerField()
    target_label = serializers.CharField()
    target_progress = serializers.IntegerField()


class AdminEventModerationActivitySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    event_id = serializers.UUIDField()
    title = serializers.CharField()
    description = serializers.CharField()
    type = serializers.ChoiceField(choices=["approved", "declined", "flagged"])
    created_at = serializers.DateTimeField()


class AdminEventPolicyHandbookSerializer(serializers.Serializer):
    title = serializers.CharField()
    description = serializers.CharField()
    cta_label = serializers.CharField()
    cta_href = serializers.CharField()
