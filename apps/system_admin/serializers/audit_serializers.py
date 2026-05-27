from django.utils import timezone
from rest_framework import serializers


class AdminAuditLogQuerySerializer(serializers.Serializer):
    date_from = serializers.DateTimeField(required=False)
    date_to = serializers.DateTimeField(required=False)
    actor_id = serializers.CharField(required=False, allow_blank=True)
    action_type = serializers.CharField(required=False, allow_blank=True)
    target_type = serializers.CharField(required=False, allow_blank=True)
    target_id = serializers.CharField(required=False, allow_blank=True)
    status = serializers.ChoiceField(choices=["success", "failed"], required=False)
    level = serializers.CharField(required=False, allow_blank=True)
    page = serializers.IntegerField(required=False, min_value=1, default=1)
    page_size = serializers.IntegerField(required=False, min_value=1, max_value=100, default=20)

    def to_service_data(self) -> dict:
        now = timezone.now()
        date_to = self.validated_data.get("date_to") or now
        date_from = self.validated_data.get("date_from") or (date_to - timezone.timedelta(hours=24))
        return {
            **self.validated_data,
            "date_from": date_from,
            "date_to": date_to,
        }


class AdminAuditExportQuerySerializer(AdminAuditLogQuerySerializer):
    export_format = serializers.ChoiceField(choices=["csv", "xlsx"], required=False, default="csv")
    date_from = serializers.DateTimeField(required=True)
    date_to = serializers.DateTimeField(required=True)


class AdminAuditActorOutputSerializer(serializers.Serializer):
    id = serializers.CharField(allow_blank=True)
    name = serializers.CharField(allow_blank=True)
    username = serializers.CharField(allow_blank=True, required=False)
    email = serializers.EmailField(allow_blank=True, required=False)


class AdminAuditTargetOutputSerializer(serializers.Serializer):
    type = serializers.CharField(allow_blank=True)
    id = serializers.CharField(allow_blank=True)


class AdminAuditLogOutputSerializer(serializers.Serializer):
    id = serializers.CharField()
    timestamp = serializers.DateTimeField()
    actor = AdminAuditActorOutputSerializer()
    action_type = serializers.CharField()
    target = AdminAuditTargetOutputSerializer()
    reason = serializers.CharField(allow_blank=True)
    status = serializers.ChoiceField(choices=["success", "failed"])
    level = serializers.CharField(allow_blank=True)
    system_module = serializers.CharField(allow_blank=True)
    trace_id = serializers.CharField(allow_blank=True)
    metadata = serializers.JSONField()


class AdminAuditSummaryOutputSerializer(serializers.Serializer):
    total_events = serializers.IntegerField()
    failed_events = serializers.IntegerField()
    high_risk_events = serializers.IntegerField()
    last_event_at = serializers.DateTimeField(allow_null=True)
    status = serializers.CharField()
