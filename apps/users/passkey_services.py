import base64
import importlib
import json
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.users.models import (
    PasskeyChallenge,
    PasskeyCredential,
    User,
    UserAuthIdentity,
)
from common.authentication import KeycloakJWTAuthentication
from common.keycloak_admin import exchange_token_for_user, get_or_create_keycloak_user


class PasskeyConfigurationError(RuntimeError):
    pass


@dataclass(frozen=True)
class PasskeyTokenResult:
    token_data: dict[str, Any]
    user: User
    credential: PasskeyCredential


class PasskeyService:
    @staticmethod
    def begin_registration(user: User) -> dict[str, Any]:
        webauthn = _load_webauthn()
        structs = _load_webauthn_structs()

        active_credentials = PasskeyCredential.objects.filter(
            user=user,
            revoked_at__isnull=True,
        )
        options = webauthn.generate_registration_options(
            rp_id=settings.PASSKEY_RP_ID,
            rp_name=settings.PASSKEY_RP_NAME,
            user_id=str(user.id).encode("utf-8"),
            user_name=user.email or user.username,
            user_display_name=user.full_name or user.email or user.username,
            authenticator_selection=structs.AuthenticatorSelectionCriteria(
                resident_key=structs.ResidentKeyRequirement.REQUIRED,
                require_resident_key=True,
                user_verification=structs.UserVerificationRequirement.PREFERRED,
            ),
            exclude_credentials=[
                structs.PublicKeyCredentialDescriptor(
                    id=webauthn.base64url_to_bytes(item.credential_id),
                    transports=_credential_transports(item, structs),
                )
                for item in active_credentials
            ],
        )
        options_payload = json.loads(webauthn.options_to_json(options))
        challenge = PasskeyService._create_challenge(
            user=user,
            email=user.email or "",
            challenge=options_payload["challenge"],
            ceremony=PasskeyChallenge.Ceremony.REGISTRATION,
        )

        return {"challenge_id": str(challenge.id), "options": options_payload}

    @staticmethod
    @transaction.atomic
    def verify_registration(
        *,
        user: User,
        challenge_id: str,
        credential: dict[str, Any],
        device_name: str = "",
    ) -> PasskeyCredential:
        webauthn = _load_webauthn()
        challenge = PasskeyService._lock_challenge(
            challenge_id=challenge_id,
            ceremony=PasskeyChallenge.Ceremony.REGISTRATION,
            user=user,
        )

        verification = PasskeyService._verify_with_origins(
            webauthn.verify_registration_response,
            credential=credential,
            expected_challenge=webauthn.base64url_to_bytes(challenge.challenge),
            expected_rp_id=settings.PASSKEY_RP_ID,
            require_user_verification=True,
        )
        credential_id = _bytes_to_base64url(verification.credential_id)
        if PasskeyCredential.objects.filter(
            credential_id=credential_id,
            revoked_at__isnull=True,
        ).exists():
            raise ValidationError({"credential": "Passkey này đã được đăng ký."})

        response = credential.get("response", {})
        transports = response.get("transports") if isinstance(response, dict) else []
        passkey = PasskeyCredential.objects.create(
            user=user,
            credential_id=credential_id,
            public_key=_bytes_to_base64url(verification.credential_public_key),
            sign_count=verification.sign_count,
            transports=transports if isinstance(transports, list) else [],
            device_name=device_name.strip()[:120],
            device_type=str(getattr(verification, "credential_device_type", "") or ""),
            backed_up=bool(getattr(verification, "credential_backed_up", False)),
        )
        UserAuthIdentity.objects.update_or_create(
            user=user,
            provider=UserAuthIdentity.Provider.PASSKEY,
            provider_subject=credential_id,
            defaults={"email_verified": True},
        )
        challenge.mark_used()
        return passkey

    @staticmethod
    def begin_authentication(email: str = "") -> dict[str, Any]:
        webauthn = _load_webauthn()
        structs = _load_webauthn_structs()

        normalized_email = email.strip().lower()
        user = None
        allow_credentials = None
        if normalized_email:
            user = User.objects.filter(email__iexact=normalized_email).first()
            credentials = PasskeyCredential.objects.filter(
                user=user,
                revoked_at__isnull=True,
            )
            allow_credentials = [
                structs.PublicKeyCredentialDescriptor(
                    id=webauthn.base64url_to_bytes(item.credential_id),
                    transports=_credential_transports(item, structs),
                )
                for item in credentials
            ]

        options = webauthn.generate_authentication_options(
            rp_id=settings.PASSKEY_RP_ID,
            allow_credentials=allow_credentials,
        )
        options_payload = json.loads(webauthn.options_to_json(options))
        challenge = PasskeyService._create_challenge(
            user=user,
            email=normalized_email,
            challenge=options_payload["challenge"],
            ceremony=PasskeyChallenge.Ceremony.AUTHENTICATION,
        )
        return {"challenge_id": str(challenge.id), "options": options_payload}

    @staticmethod
    @transaction.atomic
    def verify_authentication(
        *,
        challenge_id: str,
        credential: dict[str, Any],
        email: str = "",
    ) -> PasskeyTokenResult:
        webauthn = _load_webauthn()
        normalized_email = email.strip().lower()
        challenge = PasskeyService._lock_challenge(
            challenge_id=challenge_id,
            ceremony=PasskeyChallenge.Ceremony.AUTHENTICATION,
            email=normalized_email,
        )
        credential_id = credential.get("id") or credential.get("rawId")
        filters = {
            "credential_id": credential_id,
            "revoked_at__isnull": True,
        }
        if normalized_email:
            filters["user__email__iexact"] = normalized_email

        passkey = (
            PasskeyCredential.objects.select_related("user")
            .select_for_update()
            .filter(**filters)
            .first()
        )
        if passkey is None:
            raise ValidationError({"credential": "Passkey không hợp lệ."})

        verification = PasskeyService._verify_with_origins(
            webauthn.verify_authentication_response,
            credential=credential,
            expected_challenge=webauthn.base64url_to_bytes(challenge.challenge),
            expected_rp_id=settings.PASSKEY_RP_ID,
            credential_public_key=_base64url_to_bytes(passkey.public_key),
            credential_current_sign_count=passkey.sign_count,
            require_user_verification=True,
        )
        passkey.mark_used(
            sign_count=verification.new_sign_count,
            device_type=str(getattr(verification, "credential_device_type", "") or ""),
            backed_up=getattr(verification, "credential_backed_up", None),
        )
        challenge.mark_used()
        token_data = PasskeyService._issue_tokens(passkey.user)
        UserAuthIdentity.objects.update_or_create(
            user=passkey.user,
            provider=UserAuthIdentity.Provider.PASSKEY,
            provider_subject=passkey.credential_id,
            defaults={"email_verified": True, "last_login_at": timezone.now()},
        )
        return PasskeyTokenResult(
            token_data=token_data,
            user=passkey.user,
            credential=passkey,
        )

    @staticmethod
    def revoke_credential(*, user: User, credential_id: str) -> None:
        credential = PasskeyCredential.objects.filter(
            id=credential_id,
            user=user,
            revoked_at__isnull=True,
        ).first()
        if credential is None:
            raise ValidationError({"credential_id": "Không tìm thấy passkey."})
        credential.revoke()

    @staticmethod
    def _create_challenge(
        *,
        user: User | None,
        email: str,
        challenge: str,
        ceremony: str,
    ) -> PasskeyChallenge:
        expires_at = timezone.now() + timedelta(
            seconds=settings.PASSKEY_CHALLENGE_TTL_SECONDS,
        )
        return PasskeyChallenge.objects.create(
            user=user,
            email=email,
            challenge=challenge,
            ceremony=ceremony,
            expires_at=expires_at,
        )

    @staticmethod
    def _lock_challenge(
        *,
        challenge_id: str,
        ceremony: str,
        user: User | None = None,
        email: str = "",
    ) -> PasskeyChallenge:
        filters = {"id": challenge_id, "ceremony": ceremony}
        if user is not None:
            filters["user"] = user
        if email:
            filters["email"] = email

        challenge = (
            PasskeyChallenge.objects.select_for_update()
            .filter(**filters)
            .first()
        )
        if challenge is None or not challenge.is_usable:
            raise ValidationError({"challenge_id": "Challenge không hợp lệ hoặc đã hết hạn."})
        return challenge

    @staticmethod
    def _verify_with_origins(verify_func, **kwargs):
        last_error: Exception | None = None
        for origin in settings.PASSKEY_EXPECTED_ORIGINS:
            try:
                return verify_func(expected_origin=origin, **kwargs)
            except Exception as exc:  # py_webauthn raises typed validation errors.
                last_error = exc
        raise ValidationError({"credential": str(last_error or "Không thể xác minh passkey.")})

    @staticmethod
    def _issue_tokens(user: User) -> dict[str, Any]:
        keycloak_id = (
            UserAuthIdentity.objects.filter(
                user=user,
                provider=UserAuthIdentity.Provider.KEYCLOAK,
            )
            .values_list("provider_subject", flat=True)
            .first()
        )
        if not keycloak_id:
            keycloak_id = get_or_create_keycloak_user(user.email)

        token_data = exchange_token_for_user(keycloak_id)
        KeycloakJWTAuthentication().authenticate_token(token_data["access_token"])
        return token_data


def _load_webauthn():
    try:
        import webauthn
    except ImportError as exc:
        raise PasskeyConfigurationError(
            "Thiếu dependency webauthn. Hãy cài đặt requirements backend."
        ) from exc
    return webauthn


def _load_webauthn_structs():
    try:
        structs = importlib.import_module("webauthn.helpers.structs")
    except ImportError as exc:
        raise PasskeyConfigurationError(
            "Thiếu dependency webauthn. Hãy cài đặt requirements backend."
        ) from exc
    return structs


def _bytes_to_base64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _base64url_to_bytes(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}".encode("ascii"))


def _credential_transports(credential: PasskeyCredential, structs) -> list[Any] | None:
    values = credential.transports if isinstance(credential.transports, list) else []
    transports = []
    for value in values:
        try:
            transports.append(structs.AuthenticatorTransport(value))
        except (TypeError, ValueError):
            continue
    return transports or None
