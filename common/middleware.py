from uuid import uuid4

from django.http import JsonResponse


class RequestIdMiddleware:
    """Gắn request_id vào request/response để correlation với log/OpenSearch."""

    HEADER_NAME = 'X-Request-ID'

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = request.headers.get(self.HEADER_NAME) or uuid4().hex
        request.request_id = request_id
        response = self.get_response(request)
        response[self.HEADER_NAME] = request_id
        return response


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
            return self._error_response(
                code='unauthorized',
                message='Authentication required.',
                request_id=getattr(request, 'request_id', None),
                status_code=401,
            )

        # 403 — không phải admin
        if not self._is_admin(request.user):
            return self._error_response(
                code='forbidden',
                message='Admin access only.',
                request_id=getattr(request, 'request_id', None),
                status_code=403,
            )

        return self.get_response(request)

    @staticmethod
    def _error_response(*, code, message, request_id, status_code):
        response = JsonResponse(
            {
                'code': code,
                'message': message,
                'details': None,
                'request_id': request_id,
            },
            status=status_code,
        )
        if request_id:
            response[RequestIdMiddleware.HEADER_NAME] = request_id
        return response

    @staticmethod
    def _is_admin(user):
        """Kiểm tra user có quyền admin không."""
        if user.is_superuser:
            return True
        return user.user_roles.filter(
            role__code='admin',
            is_primary=True,
        ).exists()
