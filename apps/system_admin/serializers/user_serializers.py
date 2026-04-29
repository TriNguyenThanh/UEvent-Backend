from rest_framework import serializers
from apps.users.models import User, Role, UserRole, UserSession

class AdminRoleOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ['code', 'name', 'description']

class AdminUserRoleOutputSerializer(serializers.ModelSerializer):
    role = AdminRoleOutputSerializer(read_only=True)
    
    class Meta:
        model = UserRole
        fields = ['role', 'is_primary', 'assigned_at']


class AdminUserSessionOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSession
        fields = [
            'id', 'device_name', 'ip_address', 'user_agent', 'fcm_token',
            'expires_at', 'revoked_at', 'created_at', 'updated_at'
        ]

class AdminUserListOutputSerializer(serializers.ModelSerializer):
    user_roles = AdminUserRoleOutputSerializer(many=True, read_only=True)
    sessions = AdminUserSessionOutputSerializer(many=True, read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'full_name', 'student_code',
            'faculty', 'class_name', 'account_status', 'is_active',
            'created_at', 'updated_at', 'user_roles', 'sessions'
        ]

class AdminUserDetailOutputSerializer(serializers.ModelSerializer):
    user_roles = AdminUserRoleOutputSerializer(many=True, read_only=True)
    sessions = AdminUserSessionOutputSerializer(many=True, read_only=True)

    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'full_name', 'student_code',
            'faculty', 'class_name', 'account_status', 'is_active',
            'phone_number', 'avatar_url', 'deleted_at',
            'created_at', 'updated_at', 'user_roles', 'sessions'
        ]

class AdminUpdateUserInputSerializer(serializers.ModelSerializer):
    role_codes = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        write_only=True,
        help_text="Danh sách mã role để đồng bộ cho user"
    )

    class Meta:
        model = User
        fields = ['full_name', 'phone_number', 'student_code', 'faculty', 'class_name', 'role_codes']
        
    def to_service_data(self):
        return self.validated_data

class AdminBanUserInputSerializer(serializers.Serializer):
    reason = serializers.CharField(required=True, allow_blank=False, help_text="Lý do khóa tài khoản")

    def to_service_data(self):
        return {"reason": self.validated_data["reason"]}

class AdminUnbanUserInputSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, default="", help_text="Lý do mở khóa tài khoản")

    def to_service_data(self):
        return {"reason": self.validated_data.get("reason", "")}

class AdminAssignRoleInputSerializer(serializers.Serializer):
    role_code = serializers.CharField(required=True, help_text="Mã role cần cấp (vd: admin)")

    def to_service_data(self):
        return {"role_code": self.validated_data["role_code"]}


# ── Statistics Serializers ───────────────────────────────────────────

class StatusCountSerializer(serializers.Serializer):
    active = serializers.IntegerField()
    pending = serializers.IntegerField()
    banned = serializers.IntegerField()


class FacultyCountSerializer(serializers.Serializer):
    faculty = serializers.CharField()
    count = serializers.IntegerField()


class RoleCountSerializer(serializers.Serializer):
    role__code = serializers.CharField()
    role__name = serializers.CharField()
    count = serializers.IntegerField()


class NewUsersPerDaySerializer(serializers.Serializer):
    date = serializers.DateField()
    count = serializers.IntegerField()


class UserStatisticsOutputSerializer(serializers.Serializer):
    total_users = serializers.IntegerField(help_text="Tổng số user đang hoạt động (chưa bị xoá)")
    total_deleted = serializers.IntegerField(help_text="Tổng số user đã bị soft-delete")
    by_status = StatusCountSerializer(help_text="Phân bổ theo trạng thái tài khoản")
    by_faculty = FacultyCountSerializer(many=True, help_text="Top 10 khoa có nhiều user nhất")
    by_role = RoleCountSerializer(many=True, help_text="Phân bổ theo role")
    new_users_per_day = NewUsersPerDaySerializer(many=True, help_text="User mới đăng ký 30 ngày gần nhất")
