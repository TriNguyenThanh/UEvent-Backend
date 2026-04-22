from rest_framework.permissions import BasePermission


class IsSystemAdmin(BasePermission):
    """
    Fallback view-level permission.
    Kiểm tra user đã đăng nhập VÀ có quyền admin
    (is_superuser hoặc role 'admin').

    Lưu ý: AdminAuthMiddleware đã chặn 401/403 ở tầng middleware
    cho toàn bộ /api/v1/admin/. Permission này dùng làm backup
    cho endpoint đặc biệt hoặc khi cần object-level check.
    """
    message = 'Chỉ System Admin mới có quyền truy cập.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        return request.user.user_roles.filter(
            role__code='admin',
            is_primary=True,
        ).exists()
