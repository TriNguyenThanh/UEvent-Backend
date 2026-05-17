from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from django.conf import settings


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FcmSendResult:
    token: str
    success: bool
    error_code: str = ""
    error_message: str = ""
    invalid_token: bool = False


class FcmClient:
    INVALID_TOKEN_CODES = {
        "registration-token-not-registered",
        "invalid-registration-token",
        "invalid-argument",
        "sender-id-mismatch",
    }

    def __init__(self):
        self.enabled = bool(getattr(settings, "FCM_ENABLED", False))
        self.dry_run = bool(getattr(settings, "FCM_DRY_RUN", False))

    def send_multicast(self, *, tokens: Iterable[str], title: str, body: str, data: dict[str, str]) -> list[FcmSendResult]:
        clean_tokens = [token for token in tokens if token]
        if not clean_tokens:
            return []

        if not self.enabled:
            logger.info("FCM is disabled; marking %s token(s) as delivered in local mode.", len(clean_tokens))
            return [FcmSendResult(token=token, success=True) for token in clean_tokens]

        messaging = self._load_messaging()
        message = messaging.MulticastMessage(
            tokens=clean_tokens,
            notification=messaging.Notification(title=title, body=body),
            data={key: str(value) for key, value in data.items() if value is not None},
        )
        response = self._send(message, messaging=messaging)
        results: list[FcmSendResult] = []

        for token, send_response in zip(clean_tokens, response.responses, strict=False):
            if send_response.success:
                results.append(FcmSendResult(token=token, success=True))
                continue

            exception = send_response.exception
            error_code = str(getattr(exception, "code", "") or "")
            error_message = str(exception or "")
            results.append(
                FcmSendResult(
                    token=token,
                    success=False,
                    error_code=error_code,
                    error_message=error_message,
                    invalid_token=error_code in self.INVALID_TOKEN_CODES,
                )
            )

        return results

    def _send(self, message, *, messaging):
        if hasattr(messaging, "send_each_for_multicast"):
            return messaging.send_each_for_multicast(message, dry_run=self.dry_run)
        return messaging.send_multicast(message, dry_run=self.dry_run)

    def _load_messaging(self):
        import firebase_admin
        from firebase_admin import credentials, messaging

        if not firebase_admin._apps:
            credential = self._build_credential(credentials)
            firebase_admin.initialize_app(credential)

        return messaging

    def _build_credential(self, credentials):
        credentials_json = getattr(settings, "FIREBASE_CREDENTIALS_JSON", "")
        credentials_path = getattr(settings, "FIREBASE_CREDENTIALS_PATH", "")

        if credentials_json:
            return credentials.Certificate(json.loads(credentials_json))

        if credentials_path:
            path = Path(credentials_path)
            if not path.exists():
                raise FileNotFoundError(f"Firebase credentials file does not exist: {path}")
            return credentials.Certificate(str(path))

        raise RuntimeError("FCM_ENABLED=true nhưng chưa cấu hình FIREBASE_CREDENTIALS_PATH hoặc FIREBASE_CREDENTIALS_JSON.")
