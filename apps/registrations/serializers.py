from rest_framework import serializers

from apps.registrations.models import EventRegistration


class RegistrationCreateSerializer(serializers.Serializer):
    event_id = serializers.UUIDField()


class RegistrationEventSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    title = serializers.CharField(read_only=True)
    slug = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    visibility = serializers.CharField(read_only=True)
    start_at = serializers.DateTimeField(read_only=True)
    end_at = serializers.DateTimeField(read_only=True)
    location_snapshot = serializers.CharField(read_only=True, allow_null=True)
    cover_image_url = serializers.URLField(read_only=True, allow_null=True)


class RegistrationTicketSummarySerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    ticket_code = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    issued_at = serializers.DateTimeField(read_only=True)
    expires_at = serializers.DateTimeField(read_only=True)


class RegistrationListSerializer(serializers.ModelSerializer):
    event = serializers.SerializerMethodField()
    ticket = serializers.SerializerMethodField()

    class Meta:
        model = EventRegistration
        fields = ["id", "status", "registered_at", "cancelled_at", "event", "ticket"]
        read_only_fields = fields

    def get_event(self, obj):
        return RegistrationEventSerializer(obj.event).data

    def get_ticket(self, obj):
        ticket = getattr(obj, "ticket", None)
        if ticket is None:
            return None
        return RegistrationTicketSummarySerializer(ticket).data


class RegistrationQrSerializer(serializers.Serializer):
    registration_id = serializers.UUIDField(read_only=True)
    event_id = serializers.UUIDField(read_only=True)
    ticket_id = serializers.UUIDField(read_only=True)
    ticket_code = serializers.CharField(read_only=True)
    qr_payload = serializers.CharField(read_only=True)
    qr_signature = serializers.CharField(read_only=True)
    valid_from = serializers.DateTimeField(read_only=True)
    valid_to = serializers.DateTimeField(read_only=True)
