"""
OTP Service — sinh mã, lưu Redis cache, xác thực, gửi email SMTP.

Cache key schema:
  otp:{email}:code      → mã 6 số (TTL = OTP_TTL_SECONDS)
  otp:{email}:attempts  → số lần nhập sai (TTL = OTP_TTL_SECONDS)
  otp:{email}:cooldown  → sentinel chống gửi liên tục (TTL = OTP_COOLDOWN_SECONDS)
"""

import random
import string

from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail


# ── Cache key helpers ──────────────────────────────────────────────────────────

def _key_code(email: str) -> str:
    return f"otp:{email.lower()}:code"

def _key_attempts(email: str) -> str:
    return f"otp:{email.lower()}:attempts"

def _key_cooldown(email: str) -> str:
    return f"otp:{email.lower()}:cooldown"


# ── Public API ─────────────────────────────────────────────────────────────────

class OtpCooldownError(Exception):
    """Gửi OTP quá nhanh — vẫn còn trong cooldown window."""
    def __init__(self, remaining_seconds: int):
        self.remaining_seconds = remaining_seconds
        super().__init__(f"Vui lòng chờ {remaining_seconds} giây trước khi gửi lại.")

class OtpMaxAttemptsError(Exception):
    """Nhập sai OTP quá nhiều lần — mã bị khoá."""

class OtpInvalidError(Exception):
    """Mã OTP không đúng."""

class OtpExpiredError(Exception):
    """Mã OTP đã hết hạn."""


def send_otp(email: str) -> None:
    """
    Sinh và gửi OTP 6 chữ số đến email.
    Raise OtpCooldownError nếu gửi quá nhanh.
    """
    # Kiểm tra cooldown
    ttl = cache.ttl(_key_cooldown(email))
    if ttl and ttl > 0:
        raise OtpCooldownError(remaining_seconds=ttl)

    # Sinh mã ngẫu nhiên 6 chữ số
    code = "".join(random.choices(string.digits, k=6))

    # Lưu vào cache DB
    cache.set(_key_code(email), code, timeout=settings.OTP_TTL_SECONDS)
    cache.set(_key_attempts(email), 0, timeout=settings.OTP_TTL_SECONDS)
    cache.set(_key_cooldown(email), "1", timeout=settings.OTP_COOLDOWN_SECONDS)

    # Gửi email (console backend trong dev, SMTP trong prod)
    _send_otp_email(email, code)


def verify_otp(email: str, code: str) -> None:
    """
    Xác thực mã OTP.
    Raise:
      - OtpExpiredError   → không còn trong cache (hết 3 phút)
      - OtpMaxAttemptsError → đã sai quá nhiều lần
      - OtpInvalidError   → mã không khớp
    Nếu đúng → xoá cache để mã chỉ dùng được một lần.
    """
    stored_code = cache.get(_key_code(email))
    if stored_code is None:
        raise OtpExpiredError("Mã OTP đã hết hạn. Vui lòng yêu cầu mã mới.")

    attempts = cache.get(_key_attempts(email), 0)
    if attempts >= settings.OTP_MAX_ATTEMPTS:
        raise OtpMaxAttemptsError(
            f"Bạn đã nhập sai {settings.OTP_MAX_ATTEMPTS} lần. Vui lòng yêu cầu mã mới."
        )

    if code.strip() != stored_code:
        # Tăng counter
        cache.set(_key_attempts(email), attempts + 1, timeout=settings.OTP_TTL_SECONDS)
        remaining = settings.OTP_MAX_ATTEMPTS - attempts - 1
        raise OtpInvalidError(
            f"Mã OTP không đúng. Còn {remaining} lần thử."
        )

    # OTP đúng → xoá hết để không dùng lại được
    cache.delete(_key_code(email))
    cache.delete(_key_attempts(email))
    cache.delete(_key_cooldown(email))


# ── Email template ─────────────────────────────────────────────────────────────

def _send_otp_email(email: str, code: str) -> None:
    ttl_minutes = settings.OTP_TTL_SECONDS // 60
    subject = "Mã xác nhận UEvent của bạn"
    message = (
        f"Xin chào,\n\n"
        f"Mã xác nhận đăng nhập UEvent của bạn là:\n\n"
        f"    {code}\n\n"
        f"Mã có hiệu lực trong {ttl_minutes} phút.\n"
        f"Không chia sẻ mã này với bất kỳ ai.\n\n"
        f"Nếu bạn không yêu cầu đăng nhập, hãy bỏ qua email này.\n\n"
        f"— Đội ngũ UEvent"
    )
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=False,
    )
