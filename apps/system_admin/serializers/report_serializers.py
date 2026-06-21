from rest_framework import serializers


class AdminReportFilterSerializer(serializers.Serializer):
    from_date = serializers.DateField()
    to_date = serializers.DateField()
    group_by = serializers.CharField()


class AdminReportMetricSerializer(serializers.Serializer):
    id = serializers.CharField()
    label = serializers.CharField()
    value = serializers.IntegerField()
    helper = serializers.CharField()
    description = serializers.CharField(required=False)


class AdminReportTimeSeriesPointSerializer(serializers.Serializer):
    period = serializers.CharField()
    count = serializers.IntegerField()


class AdminReportBreakdownItemSerializer(serializers.Serializer):
    label = serializers.CharField()
    count = serializers.IntegerField()
    percentage = serializers.FloatField()


class AdminReportFunnelStepSerializer(serializers.Serializer):
    id = serializers.CharField()
    label = serializers.CharField()
    value = serializers.IntegerField()


class AdminReportCategoryPerformanceSerializer(serializers.Serializer):
    label = serializers.CharField()
    events_count = serializers.IntegerField()
    registration_count = serializers.IntegerField()


class AdminReportFacultyDistributionSerializer(serializers.Serializer):
    label = serializers.CharField()
    count = serializers.IntegerField()


class AdminReportTopEventSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    title = serializers.CharField()
    status = serializers.CharField()
    category = serializers.CharField()
    max_capacity = serializers.IntegerField()
    registration_count = serializers.IntegerField()
    checkin_count = serializers.IntegerField()
    checkin_rate = serializers.FloatField()
    capacity_rate = serializers.FloatField()


class AdminReportOrganizerRequestSummarySerializer(serializers.Serializer):
    total = serializers.IntegerField()
    pending = serializers.IntegerField()
    approved = serializers.IntegerField()
    rejected = serializers.IntegerField()
    approval_rate = serializers.FloatField()


class AdminReportHealthItemSerializer(serializers.Serializer):
    id = serializers.CharField()
    label = serializers.CharField()
    value = serializers.IntegerField()
    total = serializers.IntegerField()
    score = serializers.FloatField()


class AdminReportInsightSerializer(serializers.Serializer):
    title = serializers.CharField()
    description = serializers.CharField()
    severity = serializers.CharField()


class AdminReportOverviewSerializer(serializers.Serializer):
    generated_at = serializers.DateTimeField()
    filters = AdminReportFilterSerializer()
    metrics = AdminReportMetricSerializer(many=True)
    time_series = serializers.DictField(
        child=AdminReportTimeSeriesPointSerializer(many=True)
    )
    breakdowns = serializers.DictField(child=AdminReportBreakdownItemSerializer(many=True))
    funnel = AdminReportFunnelStepSerializer(many=True)
    category_performance = AdminReportCategoryPerformanceSerializer(many=True)
    faculty_distribution = AdminReportFacultyDistributionSerializer(many=True)
    top_events = AdminReportTopEventSerializer(many=True)
    organizer_request_summary = AdminReportOrganizerRequestSummarySerializer()
    system_health = AdminReportHealthItemSerializer(many=True)
    insights = AdminReportInsightSerializer(many=True)
