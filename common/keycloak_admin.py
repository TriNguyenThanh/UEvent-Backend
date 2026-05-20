"""
Keycloak Admin REST API client — dùng cho OTP Email Login flow.

Chức năng chính:
1. get_service_account_token() → service account token (client_credentials grant)
2. get_or_create_keycloak_user() → đảm bảo user tồn tại trong Keycloak
3. exchange_token_for_user() → dùng Token Exchange để mint Keycloak JWT cho user

Lưu ý bảo mật:
- Service account token KHÔNG được trả về cho client — chỉ dùng nội bộ.
- KEYCLOAK_ADMIN_CLIENT_SECRET phải được giữ bí mật (lưu trong .env, không commit).
- Token Exchange phải được bật trong Keycloak realm settings.
"""

from typing import Any, Dict, Optional

import requests
from django.conf import settings
from django.core.cache import cache


class KeycloakAdminError(Exception):
    """Raised khi Keycloak Admin API trả về lỗi."""

    def __init__(self, message: str, status_code: int = 0):
        super().__init__(message)
        self.status_code = status_code


_SERVICE_ACCOUNT_TOKEN_CACHE_KEY = "keycloak_admin:service_account_token"


def _get_service_account_token() -> str:
    """
    Lấy access token của service account (client_credentials grant).
    Token này dùng để gọi Keycloak Admin API — KHÔNG trả về cho client.
    """
    cached = cache.get(_SERVICE_ACCOUNT_TOKEN_CACHE_KEY)
    if cached:
        return cached

    response = requests.post(
        settings.KEYCLOAK_TOKEN_URL,
        data={
            "grant_type": "client_credentials",
            "client_id": settings.KEYCLOAK_ADMIN_CLIENT_ID,
            "client_secret": settings.KEYCLOAK_ADMIN_CLIENT_SECRET,
        },
        timeout=getattr(settings, "KEYCLOAK_TOKEN_TIMEOUT", 10),
    )
    if response.status_code != 200:
        raise KeycloakAdminError(
            f"Không lấy được service account token: {response.text}",
            status_code=response.status_code,
        )

    token_data = response.json()
    token = token_data["access_token"]
    timeout = max(int(token_data.get("expires_in", 60)) - 30, 1)
    cache.set(_SERVICE_ACCOUNT_TOKEN_CACHE_KEY, token, timeout=timeout)
    return token


def _admin_headers(service_token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {service_token}",
        "Content-Type": "application/json",
    }


def get_or_create_keycloak_user(
    email: str,
    *,
    full_name: str = "",
    first_name: str = "",
    last_name: str = "",
    avatar_url: str = "",
) -> str:
    """
    Đảm bảo user với email này tồn tại trong Keycloak.
    Trả về Keycloak user ID (UUID string).

    - Nếu user đã tồn tại → trả về ID hiện có.
    - Nếu chưa → tạo mới với emailVerified=True (đã verify qua OTP của chúng ta).
    """
    email = email.strip().lower()
    full_name = full_name.strip()
    first_name = first_name.strip()
    last_name = last_name.strip()
    avatar_url = avatar_url.strip()
    service_token = _get_service_account_token()
    headers = _admin_headers(service_token)
    base_url = settings.KEYCLOAK_ADMIN_API_URL

    user_payload = {
        "email": email,
        "username": email,
        "enabled": True,
        "emailVerified": True,
    }
    if first_name:
        user_payload["firstName"] = first_name
    if last_name:
        user_payload["lastName"] = last_name
    elif full_name:
        user_payload["firstName"] = full_name
    if avatar_url:
        user_payload["attributes"] = {"picture": [avatar_url]}

    # 1) Tìm user theo email
    search_response = requests.get(
        f"{base_url}/users",
        params={"email": email, "exact": "true"},
        headers=headers,
        timeout=10,
    )
    if search_response.status_code != 200:
        raise KeycloakAdminError(
            f"Lỗi khi tìm user trong Keycloak: {search_response.text}",
            status_code=search_response.status_code,
        )

    users = search_response.json()
    if users:
        user = users[0]
        keycloak_user_id = user["id"]
        if (
            user.get("emailVerified") is not True
            or user.get("username") != email
            or user.get("email") != email
            or user.get("enabled") is not True
            or (first_name and user.get("firstName") != first_name)
            or (last_name and user.get("lastName") != last_name)
        ):
            update_response = requests.put(
                f"{base_url}/users/{keycloak_user_id}",
                json=user_payload,
                headers=headers,
                timeout=10,
            )
            if update_response.status_code not in (200, 204):
                raise KeycloakAdminError(
                    f"Không thể cập nhật user trong Keycloak: {update_response.text}",
                    status_code=update_response.status_code,
                )
        return keycloak_user_id

    # 2) Tạo user mới
    create_response = requests.post(
        f"{base_url}/users",
        json=user_payload,
        headers=headers,
        timeout=10,
    )
    if create_response.status_code != 201:
        raise KeycloakAdminError(
            f"Không thể tạo user trong Keycloak: {create_response.text}",
            status_code=create_response.status_code,
        )

    # Lấy ID từ Location header: .../users/{uuid}
    location = create_response.headers.get("Location", "")
    keycloak_user_id = location.rstrip("/").split("/")[-1]
    if not keycloak_user_id:
        raise KeycloakAdminError("Keycloak trả về Location header không hợp lệ.")

    return keycloak_user_id


def exchange_token_for_user(keycloak_user_id: str) -> Dict[str, Any]:
    """
    Dùng Token Exchange (RFC 8693 / Keycloak impersonation) để mint
    access_token + refresh_token cho user cụ thể.

    Yêu cầu Keycloak:
    - Feature `token-exchange` phải được bật.
    - Service Account của client `KEYCLOAK_ADMIN_CLIENT_ID` cần có quyền
      `realm-management` → `impersonation`.

    Lưu ý: yêu cầu `refresh_token` để Keycloak trả đủ cả access_token và
    refresh_token cho mobile app. Nếu yêu cầu access_token, một số bản
    Keycloak chỉ trả access_token và làm app không tạo được session bền.

    Trả về dict chứa: access_token, refresh_token, expires_in, refresh_expires_in.
    """
    import logging

    logger = logging.getLogger("django")

    service_token = _get_service_account_token()

    request_data = {
        "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
        "client_id": settings.KEYCLOAK_ADMIN_CLIENT_ID,
        "client_secret": settings.KEYCLOAK_ADMIN_CLIENT_SECRET,
        "subject_token": service_token,
        "subject_token_type": "urn:ietf:params:oauth:token-type:access_token",
        "requested_token_type": "urn:ietf:params:oauth:token-type:refresh_token",
        "requested_subject": keycloak_user_id,
        "scope": settings.KEYCLOAK_SCOPE,
    }

    logger.info(
        f"Token Exchange request: client_id={settings.KEYCLOAK_ADMIN_CLIENT_ID}, "
        f"requested_subject={keycloak_user_id}"
    )

    response = requests.post(
        settings.KEYCLOAK_TOKEN_URL,
        data=request_data,
        timeout=10,
    )

    if response.status_code != 200:
        logger.error(
            f"Token Exchange failed: status={response.status_code}, "
            f"body={response.text}"
        )
        raise KeycloakAdminError(
            f"Token Exchange thất bại: {response.text}",
            status_code=response.status_code,
        )

    logger.info("Token Exchange thành công.")
    return response.json()


def logout_keycloak_refresh_token(
    refresh_token: str,
    *,
    client_id: str | None = None,
    client_secret: str | None = None,
) -> None:
    """
    Revoke a refresh token issued by the backend token-exchange client.

    OTP and native Google mobile flows receive tokens minted with
    KEYCLOAK_ADMIN_CLIENT_ID in exchange_token_for_user(), so logout must use
    the same client credentials.
    """
    client_id = client_id or settings.KEYCLOAK_ADMIN_CLIENT_ID
    client_secret = (
        settings.KEYCLOAK_ADMIN_CLIENT_SECRET
        if client_secret is None
        else client_secret
    )
    request_data = {
        "client_id": client_id,
        "refresh_token": refresh_token,
    }
    if client_secret:
        request_data["client_secret"] = client_secret

    response = requests.post(
        settings.KEYCLOAK_LOGOUT_URL,
        data=request_data,
        timeout=getattr(settings, "KEYCLOAK_TOKEN_TIMEOUT", 10),
    )
    if response.status_code not in (200, 204):
        raise KeycloakAdminError(
            f"Keycloak logout failed: {response.text}",
            status_code=response.status_code,
        )
