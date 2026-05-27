from rest_framework import serializers


class AdminSettingOutputSerializer(serializers.Serializer):
    key = serializers.CharField()
    group = serializers.CharField()
    label = serializers.CharField()
    description = serializers.CharField(allow_blank=True)
    value_type = serializers.ChoiceField(choices=["boolean", "integer", "string", "json"])
    value = serializers.JSONField()
    editable = serializers.BooleanField()
    updated_at = serializers.DateTimeField(allow_null=True)
    updated_by = serializers.CharField(allow_blank=True, allow_null=True)


class AdminSettingsGroupOutputSerializer(serializers.Serializer):
    id = serializers.CharField()
    label = serializers.CharField()
    description = serializers.CharField(allow_blank=True)


class AdminSettingsOutputSerializer(serializers.Serializer):
    groups = AdminSettingsGroupOutputSerializer(many=True)
    settings = AdminSettingOutputSerializer(many=True)


class AdminSettingUpdateItemSerializer(serializers.Serializer):
    key = serializers.CharField(max_length=100)
    value = serializers.JSONField()


class AdminSettingsUpdateInputSerializer(serializers.Serializer):
    settings = AdminSettingUpdateItemSerializer(many=True)
    reason = serializers.CharField(required=False, allow_blank=True, max_length=500)

    def to_service_data(self) -> dict:
        return {
            "settings": self.validated_data["settings"],
            "reason": self.validated_data.get("reason", ""),
        }
