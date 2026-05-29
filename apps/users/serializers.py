from rest_framework import serializers
from apps.users.models import PasskeyCredential, User


class UserProfileOutputSerializer(serializers.ModelSerializer):
    """Output serializer for mobile user profile — matches Flutter UserModel."""

    primary_role = serializers.SerializerMethodField()
    is_profile_complete = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "full_name",
            "account_status",
            "primary_role",
            "is_profile_complete",
            "phone_number",
            "student_code",
            "faculty",
            "class_name",
            "avatar_url",
        ]

    def get_primary_role(self, obj) -> str:
        primary = obj.user_roles.filter(is_primary=True).select_related("role").first()
        if primary:
            return primary.role.code
        return "student"

    def get_is_profile_complete(self, obj) -> bool:
        """
        Profile được coi là đầy đủ khi user đã điền đủ 3 trường bắt buộc:
        - full_name: tên hiển thị
        - student_code: mã số sinh viên
        - faculty: khoa / đơn vị
        """
        return bool(obj.full_name and obj.student_code and obj.faculty)


class UpdateProfileInputSerializer(serializers.Serializer):
    """Input serializer for PATCH /auth/profile."""

    full_name = serializers.CharField(max_length=255, required=False)
    phone_number = serializers.CharField(
        max_length=20, required=False, allow_blank=True
    )
    student_code = serializers.CharField(
        max_length=32, required=False, allow_blank=True, allow_null=True
    )
    faculty = serializers.CharField(
        max_length=200, required=False, allow_blank=True, allow_null=True
    )
    class_name = serializers.CharField(
        max_length=100, required=False, allow_blank=True, allow_null=True
    )


class ChangeEmailNewOtpInputSerializer(serializers.Serializer):
    """Input serializer for POST /auth/profile/email/new/otp/."""

    new_email = serializers.EmailField()
    current_otp_code = serializers.CharField(min_length=6, max_length=6)


class ChangeEmailInputSerializer(serializers.Serializer):
    """Input serializer for PATCH /auth/profile/email/."""

    new_email = serializers.EmailField()
    current_otp_code = serializers.CharField(min_length=6, max_length=6)
    new_email_otp_code = serializers.CharField(min_length=6, max_length=6)


class PasskeyRegistrationOptionsOutputSerializer(serializers.Serializer):
    challenge_id = serializers.UUIDField()
    options = serializers.JSONField()


class PasskeyRegistrationVerifyInputSerializer(serializers.Serializer):
    challenge_id = serializers.UUIDField()
    credential = serializers.JSONField()
    device_name = serializers.CharField(
        max_length=120,
        required=False,
        allow_blank=True,
    )


class PasskeyCredentialOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = PasskeyCredential
        fields = [
            "id",
            "device_name",
            "device_type",
            "backed_up",
            "transports",
            "created_at",
            "last_used_at",
            "revoked_at",
        ]


class PasskeyAuthenticationOptionsInputSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False, allow_blank=True)


class PasskeyAuthenticationOptionsOutputSerializer(serializers.Serializer):
    challenge_id = serializers.UUIDField()
    options = serializers.JSONField()


class PasskeyAuthenticationVerifyInputSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False, allow_blank=True)
    challenge_id = serializers.UUIDField()
    credential = serializers.JSONField()
