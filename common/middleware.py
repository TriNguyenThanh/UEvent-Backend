from django.http import JsonResponse


class AdminAuthMiddleware:
    """
    Gate tập trung cho admin API (/api/v1/admin/).

    - Request không thuộc admin prefix → đi qua bình thường.
    - Chưa authenticated → 401 Unauthorized.
    - Không phải admin (is_superuser hoặc role 'admin') → 403 Forbidden.

    Phải đặt SAU AuthenticationMiddleware trong settings.MIDDLEWARE
    để request.user đã được populate.
    """

    ADMIN_PREFIX = '/api/v1/admin/'

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.path.startswith(self.ADMIN_PREFIX):
            return self.get_response(request)

        # 401 — chưa đăng nhập
        if not request.user or not request.user.is_authenticated:
            return JsonResponse(
                {
                    'error': 'unauthorized',
                    'message': 'Authentication required.',
                    'status_code': 401,
                },
                status=401,
            )

        # 403 — không phải admin
        if not self._is_admin(request.user):
            return JsonResponse(
                {
                    'error': 'forbidden',
                    'message': 'Admin access only.',
                    'status_code': 403,
                },
                status=403,
            )

        return self.get_response(request)

    @staticmethod
    def _is_admin(user):
        """Kiểm tra user có quyền admin không."""
        if user.is_superuser:
            return True
        return user.user_roles.filter(
            role__code='admin',
            is_primary=True,
        ).exists()
