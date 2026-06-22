from django.utils import timezone
from rest_framework import serializers

from apps.events.models import Event
from apps.interactions.models import (
    AIQuestionAnswerJob,
    # EventFeedback,
    EventQuestion,
    EventQuestionReply,
)
# from apps.registrations.models import EventRegistration


class EventSummarySerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    title = serializers.CharField(read_only=True)
    slug = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)


class UserSummarySerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    username = serializers.CharField(read_only=True)
    full_name = serializers.CharField(read_only=True)


# class EventFeedbackSerializer(serializers.ModelSerializer):
#     event_id = serializers.PrimaryKeyRelatedField(
#         queryset=Event.objects.all(),
#         source="event",
#         write_only=True,
#         required=False,
#     )
#     event = EventSummarySerializer(read_only=True)
#     user = serializers.SerializerMethodField()
#     comment = serializers.CharField(source="content", required=False, allow_blank=True)
#     isAnonymous = serializers.BooleanField(source="is_anonymous", required=False)

#     class Meta:
#         model = EventFeedback
#         fields = [
#             "id",
#             "event_id",
#             "event",
#             "user",
#             "rating",
#             "content",
#             "comment",
#             "is_anonymous",
#             "isAnonymous",
#             "created_at",
#             "updated_at",
#         ]
#         read_only_fields = ["id", "event", "user", "created_at", "updated_at"]

#     def get_user(self, obj):
#         if obj.is_anonymous or obj.user is None:
#             return None
#         return UserSummarySerializer(obj.user).data

#     def validate(self, attrs):
#         request = self.context.get("request")
#         user = getattr(request, "user", None)
#         event = attrs.get("event") or getattr(self.instance, "event", None)

#         if request and request.method == "POST":
#             if event is None and self.context.get("event_id"):
#                 try:
#                     event = Event.objects.get(id=self.context["event_id"])
#                     attrs["event"] = event
#                 except Event.DoesNotExist as exc:
#                     raise serializers.ValidationError({"event_id": "Event not found."}) from exc
#             if event is None:
#                 raise serializers.ValidationError({"event_id": "This field is required."})
#             if event.status != Event.Status.FINISHED:
#                 raise serializers.ValidationError(
#                     {"event_id": "Chỉ có thể gửi feedback khi sự kiện đã kết thúc."}
#                 )

#             allowed_statuses = {
#                 EventRegistration.RegistrationStatus.REGISTERED,
#                 EventRegistration.RegistrationStatus.CHECKED_IN,
#             }
#             has_registration = EventRegistration.objects.filter(
#                 event=event,
#                 user=user,
#                 status__in=allowed_statuses,
#             ).exists()
#             if not has_registration:
#                 raise serializers.ValidationError(
#                     {"event_id": "Bạn chưa đăng ký tham gia sự kiện này."}
#                 )

#             if EventFeedback.objects.filter(event=event, user=user).exists():
#                 raise serializers.ValidationError(
#                     {"event_id": "Bạn đã gửi feedback cho sự kiện này."}
#                 )

#         return attrs


class EventQuestionReplySerializer(serializers.ModelSerializer):
    question_id = serializers.PrimaryKeyRelatedField(
        queryset=EventQuestion.objects.all(),
        source="question",
        write_only=True,
        required=False,
    )
    user = UserSummarySerializer(read_only=True)

    class Meta:
        model = EventQuestionReply
        fields = [
            "id",
            "question_id",
            "user",
            "content",
            "is_organizer_reply",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "user",
            "is_organizer_reply",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        request = self.context.get("request")
        if request and request.method == "POST" and not attrs.get("question"):
            question_id = self.context.get("question_id")
            if not question_id:
                raise serializers.ValidationError(
                    {"question_id": "This field is required."}
                )
            try:
                attrs["question"] = EventQuestion.objects.select_related(
                    "event"
                ).get(id=question_id)
            except EventQuestion.DoesNotExist as exc:
                raise serializers.ValidationError(
                    {"question_id": "Question not found."}
                ) from exc
        return attrs


class EventQuestionSerializer(serializers.ModelSerializer):
    event_id = serializers.PrimaryKeyRelatedField(
        queryset=Event.objects.all(),
        source="event",
        write_only=True,
        required=False,
    )
    event = EventSummarySerializer(read_only=True)
    user = serializers.SerializerMethodField()
    answered_by = UserSummarySerializer(read_only=True)
    replies = EventQuestionReplySerializer(many=True, read_only=True)

    class Meta:
        model = EventQuestion
        fields = [
            "id",
            "event_id",
            "event",
            "user",
            "question_text",
            "is_anonymous",
            "is_pinned",
            "answer_text",
            "answered_by",
            "replies",
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
            "is_pinned",
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

    def validate(self, attrs):
        request = self.context.get("request")
        if request and request.method == "POST" and not attrs.get("event"):
            event_id = self.context.get("event_id")
            if not event_id:
                raise serializers.ValidationError(
                    {"event_id": "This field is required."}
                )
            try:
                attrs["event"] = Event.objects.get(id=event_id)
            except Event.DoesNotExist as exc:
                raise serializers.ValidationError({"event_id": "Event not found."}) from exc
        return attrs


class QuestionAnswerSerializer(serializers.Serializer):
    answer_text = serializers.CharField(allow_blank=False)


class AIQuestionAnswerJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIQuestionAnswerJob
        fields = [
            "id",
            "status",
            "classification",
            "confidence",
            "draft_answer",
            "reason",
            "error_code",
            "error_message",
            "completed_at",
        ]
        read_only_fields = fields


class OrganizerEventQuestionSerializer(EventQuestionSerializer):
    ai_answer_job = AIQuestionAnswerJobSerializer(read_only=True)

    class Meta:
        model = EventQuestionSerializer.Meta.model
        fields = [*EventQuestionSerializer.Meta.fields, "ai_answer_job"]
        read_only_fields = [*EventQuestionSerializer.Meta.read_only_fields, "ai_answer_job"]
