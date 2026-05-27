from rest_framework import serializers


class AdminDashboardStatSerializer(serializers.Serializer):
    id = serializers.CharField()
    title = serializers.CharField()
    value = serializers.CharField()
    trend_label = serializers.CharField()


class AdminDashboardGrowthPointSerializer(serializers.Serializer):
    id = serializers.CharField()
    month = serializers.CharField()
    monthly_value = serializers.IntegerField()
    yearly_value = serializers.IntegerField()
    highlight = serializers.BooleanField(default=False)


class AdminDashboardQueueItemSerializer(serializers.Serializer):
    id = serializers.CharField()
    title = serializers.CharField()
    subtitle = serializers.CharField()
    status = serializers.ChoiceField(choices=["pending", "completed"])
    href = serializers.CharField()


class AdminDashboardAuditSummarySerializer(serializers.Serializer):
    total_events = serializers.IntegerField()
    failed_events = serializers.IntegerField()
    high_risk_events = serializers.IntegerField()
    last_event_at = serializers.DateTimeField(allow_null=True)
    status = serializers.CharField()


class AdminDashboardOverviewSerializer(serializers.Serializer):
    stats = AdminDashboardStatSerializer(many=True)
    growth_series = AdminDashboardGrowthPointSerializer(many=True)
    queue = AdminDashboardQueueItemSerializer(many=True)
    audit_summary = AdminDashboardAuditSummarySerializer()
