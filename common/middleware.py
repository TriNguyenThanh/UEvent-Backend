from uuid import uuid4

from django.conf import settings
from django.http import HttpResponse, JsonResponse

from common.response_codes import ResponseCode
from common.responses import build_api_response


class CorsMiddleware:
    """Thêm CORS headers cho frontend admin trong môi trường phát triển/Docker."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        origin = request.headers.get('Origin')

        if request.method == 'OPTIONS' and self._is_allowed_origin(origin):
            response = HttpResponse(status=204)
        else:
            response = self.get_response(request)

        if self._is_allowed_origin(origin):
            response['Access-Control-Allow-Origin'] = origin
            response['Vary'] = 'Origin'
            response['Access-Control-Allow-Methods'] = ', '.join(settings.CORS_ALLOWED_METHODS)
            response['Access-Control-Allow-Headers'] = ', '.join(settings.CORS_ALLOWED_HEADERS)
            response['Access-Control-Expose-Headers'] = 'Content-Disposition'
            response['Access-Control-Max-Age'] = str(settings.CORS_PREFLIGHT_MAX_AGE)
            if settings.CORS_ALLOW_CREDENTIALS:
                response['Access-Control-Allow-Credentials'] = 'true'

        return response

    @staticmethod
    def _is_allowed_origin(origin):
        return bool(origin and origin in settings.CORS_ALLOWED_ORIGINS)


class RequestIdMiddleware:
    """Gắn request_id vào request/response để correlation với log/OpenObserve."""

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
                code=ResponseCode.UNAUTHORIZED,
                message='Authentication required.',
                request_id=getattr(request, 'request_id', None),
                status_code=401,
            )

        # 403 — không phải admin
        if not self._is_admin(request.user):
            return self._error_response(
                code=ResponseCode.FORBIDDEN,
                message='Admin access only.',
                request_id=getattr(request, 'request_id', None),
                status_code=403,
            )

        return self.get_response(request)

    @staticmethod
    def _error_response(*, code, message, request_id, status_code):
        response = JsonResponse(
            build_api_response(
                success=False,
                code=code,
                message=message,
                data=None,
                errors=None,
                request_id=request_id,
            ),
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
