from rest_framework import serializers
from apps.users.models import User, Role, UserRole

class AdminRoleOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ['id', 'code', 'name', 'description']

class AdminUserRoleOutputSerializer(serializers.ModelSerializer):
    role = AdminRoleOutputSerializer(read_only=True)
    
    class Meta:
        model = UserRole
        fields = ['role', 'is_primary', 'assigned_at']

class AdminUserListOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'full_name', 'student_code',
            'faculty', 'class_name', 'account_status', 'is_active',
            'created_at', 'updated_at'
        ]

class AdminUserDetailOutputSerializer(serializers.ModelSerializer):
    user_roles = AdminUserRoleOutputSerializer(many=True, read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'full_name', 'student_code',
            'faculty', 'class_name', 'account_status', 'is_active',
            'phone_number', 'avatar_url', 'deleted_at',
            'created_at', 'updated_at', 'user_roles'
        ]

class AdminUpdateUserInputSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['full_name', 'phone_number', 'student_code', 'faculty', 'class_name']
        
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
