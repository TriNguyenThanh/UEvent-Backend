from rest_framework import serializers

from apps.events.serializers import EventCoverImageUrlMixin
from apps.events.models import EventOrganizer
from apps.registrations.models import EventRegistration
from apps.registrations.models import Ticket


class RegistrationCreateSerializer(serializers.Serializer):
    event_id = serializers.UUIDField(required=False)
    answers = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        default=list,
        allow_empty=True,
    )

    def validate(self, attrs):
        if not attrs.get("event_id") and not self.context.get("event_id"):
            raise serializers.ValidationError({"event_id": "This field is required."})
        return attrs


class RegistrationEventSerializer(EventCoverImageUrlMixin, serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    title = serializers.CharField(read_only=True)
    slug = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    visibility = serializers.CharField(read_only=True)
    start_at = serializers.DateTimeField(read_only=True)
    end_at = serializers.DateTimeField(read_only=True)
    location_snapshot = serializers.CharField(read_only=True, allow_null=True)


class RegistrationTicketSummarySerializer(serializers.Serializer):
    registration_id = serializers.UUIDField(source="registration.id", read_only=True)
    ticket_code = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    issued_at = serializers.DateTimeField(read_only=True)
    expires_at = serializers.DateTimeField(read_only=True)


class RegistrationUserSummarySerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    username = serializers.CharField(read_only=True)
    full_name = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)


class RegistrationListSerializer(serializers.ModelSerializer):
    event = serializers.SerializerMethodField()
    ticket = serializers.SerializerMethodField()
    user = serializers.SerializerMethodField()
    answers = serializers.JSONField(source="form_answers_jsonb", read_only=True)

    class Meta:
        model = EventRegistration
        fields = [
            "id",
            "status",
            "registered_at",
            "cancelled_at",
            "cancel_reason",
            "answers",
            "event",
            "user",
            "ticket",
        ]
        read_only_fields = fields

    def get_event(self, obj):
        return RegistrationEventSerializer(obj.event).data

    def get_ticket(self, obj):
        ticket = getattr(obj, "ticket", None)
        if ticket is None:
            return None
        return RegistrationTicketSummarySerializer(ticket).data

    def get_user(self, obj):
        return RegistrationUserSummarySerializer(obj.user).data


class RegistrationCancelSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=500)


class EventRoleSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    event_id = serializers.UUIDField(source="event.id", read_only=True)

    class Meta:
        model = EventOrganizer
        fields = ["id", "event_id", "user", "organizer_role", "joined_at"]
        read_only_fields = fields

    def get_user(self, obj):
        return RegistrationUserSummarySerializer(obj.user).data


class RegistrationQrSerializer(serializers.Serializer):
    registration_id = serializers.UUIDField(read_only=True)
    event_id = serializers.UUIDField(read_only=True)
    ticket_code = serializers.CharField(read_only=True)
    qr_payload = serializers.CharField(read_only=True)
    qr_signature = serializers.CharField(read_only=True)
    valid_from = serializers.DateTimeField(read_only=True)
    valid_to = serializers.DateTimeField(read_only=True)


class TicketUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = ["status", "expires_at"]
        extra_kwargs = {
            "status": {"required": False},
            "expires_at": {"required": False},
        }


class TicketDetailSerializer(serializers.ModelSerializer):
    registration_id = serializers.UUIDField(source="registration.id", read_only=True)
    event = serializers.SerializerMethodField()

    class Meta:
        model = Ticket
        fields = [
            "registration_id",
            "ticket_code",
            "status",
            "issued_at",
            "used_at",
            "expires_at",
            "event",
        ]
        read_only_fields = fields

    def get_event(self, obj):
        return RegistrationEventSerializer(obj.registration.event).data
