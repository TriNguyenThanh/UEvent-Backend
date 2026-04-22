import logging
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken

from common.exceptions import UnauthorizedError, ForbiddenError

audit_logger = logging.getLogger("uevent.audit")


class AdminAuthService:
    """Service xử lý logic đăng nhập cho Admin."""

    @staticmethod
    def admin_login(*, username: str, password: str) -> dict:
        """
        Xác thực admin/staff user và trả về JWT tokens.

        Returns:
            dict chứa access, refresh tokens và thông tin user cơ bản.
        Raises:
            UnauthorizedError: Nếu thông tin đăng nhập không hợp lệ.
            ForbiddenError: Nếu user không có quyền admin (is_staff/is_superuser).
        """
        user = authenticate(username=username, password=password)

        if user is None:
            raise UnauthorizedError("Tên đăng nhập hoặc mật khẩu không đúng.")

        if not user.is_active:
            raise UnauthorizedError("Tài khoản đã bị vô hiệu hóa.")

        if not (user.is_staff or user.is_superuser):
            raise ForbiddenError("Chỉ quản trị viên mới có quyền truy cập.")

        refresh = RefreshToken.for_user(user)

        audit_logger.info(
            "Admin login success",
            extra={
                "action_type": "admin_login",
                "actor_id": str(user.pk),
                "target_type": "users.User",
                "target_id": str(user.pk),
                "system_module": "system_admin",
            },
        )

        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "id": str(user.pk),
                "username": user.username,
                "full_name": user.full_name,
                "email": user.email,
                "avatar_url": user.avatar_url,
                "is_superuser": user.is_superuser,
            },
        }
