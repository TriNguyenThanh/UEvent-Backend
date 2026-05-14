from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken

from common.exceptions import UnauthorizedError, ForbiddenError
from common.response_codes import ResponseCode
from .audit_service import AdminAuditService


class AdminAuthService:
    """Service xử lý logic đăng nhập/đăng xuất cho Admin."""

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
            raise UnauthorizedError(code=ResponseCode.INVALID_CREDENTIALS, detail="Thông tin đăng nhập không hợp lệ.")

        if not user.is_active:
            raise UnauthorizedError(code=ResponseCode.ACCOUNT_DISABLED, detail="Tài khoản đã bị vô hiệu hóa.")

        if not (user.is_staff or user.is_superuser):
            raise ForbiddenError(code=ResponseCode.INSUFFICIENT_PERMISSIONS, detail="Chỉ quản trị viên mới có quyền truy cập.")

        refresh = RefreshToken.for_user(user)

        AdminAuditService.log_action(
            action="admin_login",
            actor=user,
            target_type="users.User",
            target_id=str(user.pk),
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

    @staticmethod
    def admin_logout(*, actor) -> None:
        """Ghi audit logout stateless cho quản trị viên."""
        AdminAuditService.log_action(
            action="admin_logout",
            actor=actor,
            target_type="users.User",
            target_id=str(actor.pk),
        )
