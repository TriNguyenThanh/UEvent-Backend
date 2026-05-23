from rest_framework import serializers

from apps.registrations.models import CheckinLog, EventRegistration, Ticket


class AdminTicketUserSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    username = serializers.CharField(read_only=True)
    full_name = serializers.CharField(read_only=True, allow_blank=True)
    email = serializers.EmailField(read_only=True)
    student_code = serializers.CharField(read_only=True, allow_blank=True, allow_null=True)


class AdminTicketEventSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    title = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    start_at = serializers.DateTimeField(read_only=True)
    end_at = serializers.DateTimeField(read_only=True)
    location_snapshot = serializers.CharField(read_only=True, allow_blank=True, allow_null=True)


class AdminTicketRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventRegistration
        fields = ["id", "status", "registered_at", "cancelled_at", "cancel_reason"]
        read_only_fields = fields


class AdminCheckinLogOutputSerializer(serializers.ModelSerializer):
    scanner_user = serializers.SerializerMethodField()

    class Meta:
        model = CheckinLog
        fields = ["id", "result", "note", "checked_in_at", "scanner_user"]
        read_only_fields = fields

    def get_scanner_user(self, obj):
        if obj.scanner_user is None:
            return None
        return AdminTicketUserSerializer(obj.scanner_user).data


class AdminTicketOutputSerializer(serializers.ModelSerializer):
    event = serializers.SerializerMethodField()
    user = serializers.SerializerMethodField()
    registration = serializers.SerializerMethodField()
    checkins = serializers.SerializerMethodField()

    class Meta:
        model = Ticket
        fields = [
            "id",
            "ticket_code",
            "status",
            "issued_at",
            "used_at",
            "expires_at",
            "event",
            "user",
            "registration",
            "checkins",
        ]
        read_only_fields = fields

    def get_event(self, obj):
        return AdminTicketEventSerializer(obj.registration.event).data

    def get_user(self, obj):
        return AdminTicketUserSerializer(obj.registration.user).data

    def get_registration(self, obj):
        return AdminTicketRegistrationSerializer(obj.registration).data

    def get_checkins(self, obj):
        logs = getattr(obj, "prefetched_checkins", None)
        if logs is None:
            logs = obj.checkin_logs.select_related("scanner_user").order_by("-checked_in_at", "-created_at")
        return AdminCheckinLogOutputSerializer(logs, many=True).data


class AdminTicketStatisticsOutputSerializer(serializers.Serializer):
    total_tickets = serializers.IntegerField()
    valid_tickets = serializers.IntegerField()
    used_tickets = serializers.IntegerField()
    cancelled_tickets = serializers.IntegerField()
    expired_tickets = serializers.IntegerField()
    total_registrations = serializers.IntegerField()
    checked_in_registrations = serializers.IntegerField()
    checkins_today = serializers.IntegerField()
    checkin_rate = serializers.FloatField()


class AdminTicketCancelInputSerializer(serializers.Serializer):
    reason = serializers.CharField(required=True, allow_blank=False, max_length=500)


class AdminTicketScanInputSerializer(serializers.Serializer):
    event_id = serializers.UUIDField()
    ticket_code = serializers.CharField(required=False, allow_blank=True, max_length=100)
    qr_payload = serializers.CharField(required=False, allow_blank=True)
    qr_signature = serializers.CharField(required=False, allow_blank=True)
    note = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=500)

    def validate(self, attrs):
        if not attrs.get("ticket_code") and not attrs.get("qr_payload"):
            raise serializers.ValidationError({"ticket": "Cần nhập mã vé hoặc QR payload."})
        return attrs


class AdminTicketScanResultSerializer(serializers.Serializer):
    result = serializers.CharField()
    log = AdminCheckinLogOutputSerializer()
    ticket = AdminTicketOutputSerializer(allow_null=True)
    registration = AdminTicketRegistrationSerializer(allow_null=True)
    event = AdminTicketEventSerializer()
