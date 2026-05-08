from rest_framework import serializers


class AdminLoginInputSerializer(serializers.Serializer):
    """Serializer xác thực đầu vào cho Admin Login."""
    username = serializers.CharField(
        required=True,
        help_text="Tên đăng nhập của quản trị viên.",
    )
    password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'},
        help_text="Mật khẩu.",
    )


class AdminUserInfoOutputSerializer(serializers.Serializer):
    """Thông tin user rút gọn trả về sau khi đăng nhập."""
    id = serializers.UUIDField()
    username = serializers.CharField()
    full_name = serializers.CharField()
    email = serializers.EmailField()
    avatar_url = serializers.URLField(allow_blank=True)
    is_superuser = serializers.BooleanField()


class AdminLoginOutputSerializer(serializers.Serializer):
    """Serializer response cho Admin Login."""
    access = serializers.CharField(help_text="JWT Access Token.")
    refresh = serializers.CharField(help_text="JWT Refresh Token.")
    user = AdminUserInfoOutputSerializer(help_text="Thông tin quản trị viên.")
