from django.utils import timezone
from rest_framework import serializers

from apps.events.models import Event
from apps.interactions.models import EventFeedback, EventQuestion
from apps.registrations.models import EventRegistration


class EventSummarySerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    title = serializers.CharField(read_only=True)
    slug = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)


class UserSummarySerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    username = serializers.CharField(read_only=True)
    full_name = serializers.CharField(read_only=True)


class EventFeedbackSerializer(serializers.ModelSerializer):
    event_id = serializers.PrimaryKeyRelatedField(
        queryset=Event.objects.all(),
        source="event",
        write_only=True,
    )
    event = EventSummarySerializer(read_only=True)
    user = serializers.SerializerMethodField()

    class Meta:
        model = EventFeedback
        fields = [
            "id",
            "event_id",
            "event",
            "user",
            "rating",
            "content",
            "is_anonymous",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "event", "user", "created_at", "updated_at"]

    def get_user(self, obj):
        if obj.is_anonymous or obj.user is None:
            return None
        return UserSummarySerializer(obj.user).data

    def validate(self, attrs):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        event = attrs.get("event") or getattr(self.instance, "event", None)

        if request and request.method == "POST":
            if event.status != Event.Status.FINISHED:
                raise serializers.ValidationError(
                    {"event_id": "Chỉ có thể gửi feedback khi sự kiện đã kết thúc."}
                )

            allowed_statuses = {
                EventRegistration.RegistrationStatus.REGISTERED,
                EventRegistration.RegistrationStatus.CHECKED_IN,
            }
            has_registration = EventRegistration.objects.filter(
                event=event,
                user=user,
                status__in=allowed_statuses,
            ).exists()
            if not has_registration:
                raise serializers.ValidationError(
                    {"event_id": "Bạn chưa đăng ký tham gia sự kiện này."}
                )

            if EventFeedback.objects.filter(event=event, user=user).exists():
                raise serializers.ValidationError(
                    {"event_id": "Bạn đã gửi feedback cho sự kiện này."}
                )

        return attrs


class EventQuestionSerializer(serializers.ModelSerializer):
    event_id = serializers.PrimaryKeyRelatedField(
        queryset=Event.objects.all(),
        source="event",
        write_only=True,
    )
    event = EventSummarySerializer(read_only=True)
    user = serializers.SerializerMethodField()
    answered_by = UserSummarySerializer(read_only=True)

    class Meta:
        model = EventQuestion
        fields = [
            "id",
            "event_id",
            "event",
            "user",
            "question_text",
            "is_anonymous",
            "answer_text",
            "answered_by",
            "moderation_status",
            "asked_at",
            "answered_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "event",
            "user",
            "answered_by",
            "asked_at",
            "answered_at",
            "created_at",
            "updated_at",
        ]

    def get_user(self, obj):
        if obj.is_anonymous or obj.user is None:
            return None
        return UserSummarySerializer(obj.user).data

    def update(self, instance, validated_data):
        answer_text = validated_data.get("answer_text")
        if answer_text and answer_text != instance.answer_text:
            request = self.context.get("request")
            instance.answered_by = getattr(request, "user", None)
            instance.answered_at = timezone.now()
        if answer_text == "":
            instance.answered_by = None
            instance.answered_at = None
        return super().update(instance, validated_data)
