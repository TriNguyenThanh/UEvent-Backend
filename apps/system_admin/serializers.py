from rest_framework import serializers
class BanUserInputSerializer(serializers.Serializer):
    user_id = serializers.UUIDField(required=True, help_text="ID of the user to ban")
    reason = serializers.CharField(required=False, allow_blank=True, help_text="Reason for banning the user")

    def to_service_data(self):
        return {
            "target_user_id": self.validated_data["user_id"],
            "reason": self.validated_data["reason"],
        }
