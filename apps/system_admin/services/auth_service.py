from typing import Any

import requests
from django.conf import settings

from common.authentication import KeycloakJWTAuthentication
from common.exceptions import BaseAPIException, ForbiddenError, UnauthorizedError
from common.keycloak_admin import logout_keycloak_refresh_token
from common.response_codes import ResponseCode
from .audit_service import AdminAuditService


class AdminAuthService:
    """Service xử lý đăng nhập/đăng xuất admin qua Keycloak."""

    @staticmethod
    def admin_login(*, username: str, password: str) -> dict:
        """Đổi username/password lấy token Keycloak, sync user local và kiểm tra quyền admin."""
        token_data = AdminAuthService._request_token(
            {
                "grant_type": "password",
                "username": username,
                "password": password,
                "scope": settings.KEYCLOAK_SCOPE,
            }
        )
        user, _ = AdminAuthService._authenticate_access_token(
            token_data["access_token"]
        )
        AdminAuthService._ensure_admin_user(user)

        AdminAuditService.log_action(
            action="admin_login",
            actor=user,
            target_type="users.User",
            target_id=str(user.pk),
        )

        return {
            "access": token_data["access_token"],
            "refresh": token_data["refresh_token"],
            "user": AdminAuthService._serialize_user(user),
        }

    @staticmethod
    def refresh_token(*, refresh: str) -> dict:
        """Đổi Keycloak refresh token lấy access token mới và kiểm tra lại quyền admin."""
        token_data = AdminAuthService._request_token(
            {
                "grant_type": "refresh_token",
                "refresh_token": refresh,
            }
        )
        user, _ = AdminAuthService._authenticate_access_token(
            token_data["access_token"]
        )
        AdminAuthService._ensure_admin_user(user)

        result = {"access": token_data["access_token"]}
        if token_data.get("refresh_token"):
            result["refresh"] = token_data["refresh_token"]
        return result

    @staticmethod
    def admin_logout(*, actor, refresh: str | None = None) -> None:
        """Ghi audit logout và thu hồi refresh token Keycloak nếu client gửi kèm."""
        if refresh:
            AdminAuthService._logout_keycloak_refresh_token(refresh)

        AdminAuditService.log_action(
            action="admin_logout",
            actor=actor,
            target_type="users.User",
            target_id=str(actor.pk),
        )

    @staticmethod
    def _request_token(payload: dict[str, str]) -> dict[str, Any]:
        data = {
            "client_id": settings.KEYCLOAK_CLIENT_ID,
            **payload,
        }
        if settings.KEYCLOAK_CLIENT_SECRET:
            data["client_secret"] = settings.KEYCLOAK_CLIENT_SECRET

        try:
            response = requests.post(
                settings.KEYCLOAK_TOKEN_URL,
                data=data,
                timeout=settings.KEYCLOAK_TOKEN_TIMEOUT,
            )
        except requests.RequestException as exc:
            raise BaseAPIException(
                code=ResponseCode.SERVICE_UNAVAILABLE,
                detail="Không thể kết nối Keycloak.",
                status_code=503,
            ) from exc

        if response.status_code in (400, 401):
            raise UnauthorizedError(
                code=ResponseCode.INVALID_CREDENTIALS,
                detail="Thông tin đăng nhập không hợp lệ.",
            )

        if response.status_code >= 500:
            raise BaseAPIException(
                code=ResponseCode.SERVICE_UNAVAILABLE,
                detail="Keycloak tạm thời không khả dụng.",
                status_code=503,
            )

        try:
            token_data = response.json()
        except ValueError as exc:
            raise BaseAPIException(
                code=ResponseCode.SERVICE_UNAVAILABLE,
                detail="Keycloak trả về dữ liệu không hợp lệ.",
                status_code=503,
            ) from exc

        if "access_token" not in token_data:
            raise UnauthorizedError(
                code=ResponseCode.INVALID_CREDENTIALS,
                detail="Keycloak không trả về access token hợp lệ.",
            )

        return token_data

    @staticmethod
    def _logout_keycloak_refresh_token(refresh: str) -> None:
        try:
            logout_keycloak_refresh_token(
                refresh,
                client_id=settings.KEYCLOAK_CLIENT_ID,
                client_secret=settings.KEYCLOAK_CLIENT_SECRET,
            )
        except Exception:
            pass

    @staticmethod
    def _authenticate_access_token(access_token: str):
        try:
            return KeycloakJWTAuthentication().authenticate_token(access_token)
        except Exception as exc:
            raise UnauthorizedError(
                code=ResponseCode.INVALID_CREDENTIALS,
                detail="Keycloak access token không hợp lệ.",
            ) from exc

    @staticmethod
    def _ensure_admin_user(user) -> None:
        if not user.is_active:
            raise UnauthorizedError(
                code=ResponseCode.ACCOUNT_DISABLED,
                detail="Tài khoản đã bị vô hiệu hóa.",
            )

        if not (user.is_staff or user.is_superuser):
            raise ForbiddenError(
                code=ResponseCode.INSUFFICIENT_PERMISSIONS,
                detail="Chỉ quản trị viên mới có quyền truy cập.",
            )

    @staticmethod
    def _serialize_user(user) -> dict:
        return {
            "id": str(user.pk),
            "username": user.username,
            "full_name": user.full_name,
            "email": user.email,
            "avatar_url": user.avatar_url,
            "is_superuser": user.is_superuser,
        }
