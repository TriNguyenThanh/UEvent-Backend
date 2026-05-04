from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.system_admin.models import ExportJob
from apps.users.models import User, Role, UserRole, UserSession
from apps.system_admin.services.user_export_service import AdminUserExportService


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

class AdminCreateUserInputSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'},
        help_text="Mật khẩu tạm cho user mới.",
    )
    role_codes = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        write_only=True,
        help_text="Danh sách mã role cần gán cho user mới.",
    )

    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'full_name', 'student_code',
            'phone_number', 'faculty', 'class_name', 'role_codes',
        ]

    def validate_username(self, value):
        if User.all_objects.filter(username=value).exists():
            raise serializers.ValidationError("Tên đăng nhập đã tồn tại.")
        return value

    def validate_email(self, value):
        if User.all_objects.filter(email=value).exists():
            raise serializers.ValidationError("Email đã tồn tại.")
        return value

    def validate_student_code(self, value):
        if value and User.all_objects.filter(student_code=value).exists():
            raise serializers.ValidationError("Mã sinh viên đã tồn tại.")
        return value

    def validate(self, attrs):
        try:
            validate_password(attrs["password"])
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)}) from exc
        return attrs

    def to_service_data(self):
        return dict(self.validated_data)


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


class AdminUserExportRequestSerializer(serializers.Serializer):
    format = serializers.ChoiceField(
        choices=ExportJob.ExportFormat.choices,
        required=False,
        default=ExportJob.ExportFormat.CSV,
        help_text="Định dạng file export.",
    )
    filters = serializers.DictField(
        child=serializers.JSONField(),
        required=False,
        default=dict,
        help_text="Bộ lọc export user: account_status, faculty, is_active, search.",
    )
    fields = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=False,
        help_text="Danh sách field cần export.",
    )

    def validate_filters(self, value):
        unsupported = sorted(set(value.keys()) - AdminUserExportService.ALLOWED_FILTERS)
        if unsupported:
            raise serializers.ValidationError(f"Bộ lọc không được hỗ trợ: {', '.join(unsupported)}.")
        return value

    def validate_fields(self, value):
        deduped_fields = list(dict.fromkeys(value))
        unsupported = sorted(set(deduped_fields) - AdminUserExportService.ALLOWED_FIELDS)
        if unsupported:
            raise serializers.ValidationError(f"Field export không được hỗ trợ: {', '.join(unsupported)}.")
        return deduped_fields

    def validate(self, attrs):
        filters = attrs.get("filters") or {}
        account_status = filters.get("account_status")
        if account_status and account_status not in User.AccountStatus.values:
            raise serializers.ValidationError({"filters": {"account_status": "Trạng thái tài khoản không hợp lệ."}})

        if "is_active" in filters and not isinstance(filters["is_active"], bool):
            raise serializers.ValidationError({"filters": {"is_active": "Giá trị is_active phải là boolean."}})

        return attrs

    def to_service_data(self):
        return dict(self.validated_data)


class AdminExportJobOutputSerializer(serializers.ModelSerializer):
    job_id = serializers.UUIDField(source="id", read_only=True)
    eta_seconds = serializers.SerializerMethodField()

    class Meta:
        model = ExportJob
        fields = [
            "job_id",
            "export_type",
            "format",
            "status",
            "progress",
            "retry_count",
            "error_code",
            "error_message",
            "file_key",
            "download_url",
            "file_size_bytes",
            "checksum_sha256",
            "rows_count",
            "eta_seconds",
            "expires_at",
            "started_at",
            "completed_at",
            "created_at",
            "updated_at",
        ]

    format = serializers.CharField(source="export_format", read_only=True)

    def get_eta_seconds(self, obj):
        if obj.status in {ExportJob.Status.COMPLETED, ExportJob.Status.FAILED, ExportJob.Status.EXPIRED}:
            return 0
        return 60


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
