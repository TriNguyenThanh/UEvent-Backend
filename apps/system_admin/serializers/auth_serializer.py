from rest_framework import serializers


class AdminUserInfoOutputSerializer(serializers.Serializer):
    """Thông tin user rút gọn trả về sau khi đăng nhập."""
    id = serializers.UUIDField()
    username = serializers.CharField()
    full_name = serializers.CharField()
    email = serializers.EmailField()
    avatar_url = serializers.URLField(allow_blank=True)
    is_superuser = serializers.BooleanField()
