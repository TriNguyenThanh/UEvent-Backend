from rest_framework import serializers

from apps.events.serializers import EventCoverImageUrlMixin
from apps.events.models import EventOrganizer
from apps.registrations.models import CheckinLog, EventRegistration
from apps.registrations.models import Ticket
from apps.users.services import UserService


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
    avatar_url = serializers.SerializerMethodField()

    def get_avatar_url(self, obj):
        return (obj.avatar_url or "").strip() or UserService.build_generated_avatar_url(
            obj
        )


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
    reason = serializers.CharField(
        required=False, allow_blank=True, allow_null=True, max_length=500
    )


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


class EventCheckinScanInputSerializer(serializers.Serializer):
    ticket_code = serializers.CharField(
        required=False, allow_blank=True, max_length=100
    )
    email = serializers.EmailField(required=False, allow_blank=True)
    qr_payload = serializers.CharField(required=False, allow_blank=True)
    qr_signature = serializers.CharField(required=False, allow_blank=True)
    note = serializers.CharField(
        required=False, allow_blank=True, allow_null=True, max_length=500
    )

    def validate(self, attrs):
        if (
            not attrs.get("ticket_code")
            and not attrs.get("email")
            and not attrs.get("qr_payload")
        ):
            raise serializers.ValidationError(
                {"ticket": "Cần nhập email, mã vé hoặc QR payload."}
            )
        return attrs


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


class EventCheckinTicketSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)
    registration_id = serializers.UUIDField(source="registration.id", read_only=True)

    class Meta:
        model = Ticket
        fields = [
            "id",
            "registration_id",
            "ticket_code",
            "status",
            "issued_at",
            "used_at",
            "expires_at",
        ]
        read_only_fields = fields


class EventCheckinLogSerializer(serializers.ModelSerializer):
    scanner_user = serializers.SerializerMethodField()
    ticket = serializers.SerializerMethodField()
    registration = serializers.SerializerMethodField()

    class Meta:
        model = CheckinLog
        fields = [
            "id",
            "result",
            "note",
            "checked_in_at",
            "scanner_user",
            "ticket",
            "registration",
        ]
        read_only_fields = fields

    def get_scanner_user(self, obj):
        if obj.scanner_user is None:
            return None
        return RegistrationUserSummarySerializer(obj.scanner_user).data

    def get_ticket(self, obj):
        if obj.ticket is None:
            return None
        return EventCheckinTicketSerializer(obj.ticket).data

    def get_registration(self, obj):
        if obj.ticket is None:
            return None
        return RegistrationListSerializer(obj.ticket.registration).data


class EventCheckinScanResultSerializer(serializers.Serializer):
    result = serializers.CharField()
    log = EventCheckinLogSerializer()
    ticket = EventCheckinTicketSerializer(allow_null=True)
    registration = RegistrationListSerializer(allow_null=True)
    event = RegistrationEventSerializer()
