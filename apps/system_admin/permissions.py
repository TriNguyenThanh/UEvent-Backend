from rest_framework.permissions import BasePermission


class IsAdminOrSuperUser(BasePermission):
    """
    DRF Permission: cho phép truy cập nếu user là staff hoặc superuser.
    Thay thế AdminAuthMiddleware — kiểm tra quyền ở tầng View chuẩn DRF.
    """
    message = "Chỉ quản trị viên mới có quyền truy cập."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.is_staff or request.user.is_superuser