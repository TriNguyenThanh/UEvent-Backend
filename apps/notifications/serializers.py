from rest_framework import serializers


class NotificationInboxOutputSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    notification_id = serializers.UUIDField()
    event_id = serializers.UUIDField(allow_null=True)
    title = serializers.CharField()
    message = serializers.CharField()
    type = serializers.CharField()
    delivery_status = serializers.CharField()
    delivered_at = serializers.DateTimeField(allow_null=True)
    read_at = serializers.DateTimeField(allow_null=True)
    action_label = serializers.CharField(allow_blank=True, allow_null=True)
    action_route = serializers.CharField(allow_blank=True, allow_null=True)
    created_at = serializers.DateTimeField()


class DeviceRegistrationInputSerializer(serializers.Serializer):
    fcm_token = serializers.CharField(max_length=512, required=True, allow_blank=False, trim_whitespace=True)
    device_name = serializers.CharField(max_length=120, required=False, allow_blank=True, trim_whitespace=True)


class DeviceUnregistrationInputSerializer(serializers.Serializer):
    fcm_token = serializers.CharField(max_length=512, required=True, allow_blank=False, trim_whitespace=True)
