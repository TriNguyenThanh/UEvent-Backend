from rest_framework import serializers


class AdminLoginInputSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class AdminTokenRefreshInputSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class AdminLogoutInputSerializer(serializers.Serializer):
    refresh = serializers.CharField(required=False, allow_blank=True)


class AdminUserInfoOutputSerializer(serializers.Serializer):
    """Thông tin user rút gọn trả về sau khi đăng nhập."""
    id = serializers.UUIDField()
    username = serializers.CharField()
    full_name = serializers.CharField()
    email = serializers.EmailField()
    avatar_url = serializers.URLField(allow_blank=True)
    is_superuser = serializers.BooleanField()


class AdminLoginOutputSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = AdminUserInfoOutputSerializer()


class AdminTokenRefreshOutputSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField(required=False)
