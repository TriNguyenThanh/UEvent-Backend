from rest_framework import serializers
from apps.users.models import User


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
    phone_number = serializers.CharField(max_length=20, required=False, allow_blank=True)
    student_code = serializers.CharField(max_length=32, required=False, allow_blank=True, allow_null=True)
    faculty = serializers.CharField(max_length=200, required=False, allow_blank=True, allow_null=True)
    class_name = serializers.CharField(max_length=100, required=False, allow_blank=True, allow_null=True)
