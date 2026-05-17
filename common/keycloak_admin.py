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


class KeycloakAdminError(Exception):
    """Raised khi Keycloak Admin API trả về lỗi."""

    def __init__(self, message: str, status_code: int = 0):
        super().__init__(message)
        self.status_code = status_code


def _get_service_account_token() -> str:
    """
    Lấy access token của service account (client_credentials grant).
    Token này dùng để gọi Keycloak Admin API — KHÔNG trả về cho client.
    """
    response = requests.post(
        settings.KEYCLOAK_TOKEN_URL,
        data={
            "grant_type": "client_credentials",
            "client_id": settings.KEYCLOAK_ADMIN_CLIENT_ID,
            "client_secret": settings.KEYCLOAK_ADMIN_CLIENT_SECRET,
        },
        timeout=10,
    )
    if response.status_code != 200:
        raise KeycloakAdminError(
            f"Không lấy được service account token: {response.text}",
            status_code=response.status_code,
        )
    return response.json()["access_token"]


def _admin_headers(service_token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {service_token}",
        "Content-Type": "application/json",
    }


def get_or_create_keycloak_user(email: str) -> str:
    """
    Đảm bảo user với email này tồn tại trong Keycloak.
    Trả về Keycloak user ID (UUID string).

    - Nếu user đã tồn tại → trả về ID hiện có.
    - Nếu chưa → tạo mới với emailVerified=True (đã verify qua OTP của chúng ta).
    """
    service_token = _get_service_account_token()
    headers = _admin_headers(service_token)
    base_url = settings.KEYCLOAK_ADMIN_API_URL

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
        return users[0]["id"]

    # 2) Tạo user mới
    create_response = requests.post(
        f"{base_url}/users",
        json={
            "email": email,
            "username": email,  # Keycloak yêu cầu username
            "enabled": True,
            "emailVerified": True,  # OTP đã xác nhận email → đánh dấu verified
        },
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

    Lưu ý: KHÔNG gửi `audience` — khi dùng `requested_subject` (impersonation),
    Keycloak tự issue token dưới requesting client. Gửi sai audience
    sẽ gây lỗi `unknown_error`.

    Trả về dict chứa: access_token, refresh_token, expires_in, refresh_expires_in.
    """
    import logging
    logger = logging.getLogger('django')

    service_token = _get_service_account_token()

    request_data = {
        "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
        "client_id": settings.KEYCLOAK_ADMIN_CLIENT_ID,
        "client_secret": settings.KEYCLOAK_ADMIN_CLIENT_SECRET,
        "subject_token": service_token,
        "subject_token_type": "urn:ietf:params:oauth:token-type:access_token",
        "requested_token_type": "urn:ietf:params:oauth:token-type:access_token",
        "requested_subject": keycloak_user_id,
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

