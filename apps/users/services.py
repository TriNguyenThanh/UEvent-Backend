from typing import Any

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed

from apps.users.models import Role, UserAuthIdentity, UserRole


class UserService:
    """Business logic for mobile user operations."""

    @staticmethod
    def update_profile(user, validated_data: dict):
        """Update user profile fields from validated PATCH data."""
        update_fields = []

        for field_name in ("full_name", "phone_number", "student_code", "faculty", "class_name"):
            if field_name in validated_data:
                setattr(user, field_name, validated_data[field_name])
                update_fields.append(field_name)

        if update_fields:
            with transaction.atomic():
                user.save(update_fields=update_fields)

        return user


class KeycloakProvisioningService:
    """Provision and sync local users from validated Keycloak JWT payloads."""

    DEFAULT_ROLE_CODE = "student"

    @classmethod
    def provision_from_payload(cls, payload: dict[str, Any]):
        subject = cls._require_subject(payload)
        email = cls._require_verified_email(payload)
        full_name = cls._extract_full_name(payload)
        avatar_url = cls._extract_avatar_url(payload)

        User = get_user_model()

        with transaction.atomic():
            identity = (
                UserAuthIdentity.all_objects.select_for_update()
                .select_related("user")
                .filter(
                    provider=UserAuthIdentity.Provider.KEYCLOAK,
                    provider_subject=subject,
                )
                .first()
            )

            if identity is None:
                user = cls._get_or_create_user_for_email(
                    User=User,
                    email=email,
                    full_name=full_name,
                )
                identity = UserAuthIdentity.objects.create(
                    user=user,
                    provider=UserAuthIdentity.Provider.KEYCLOAK,
                    provider_subject=subject,
                    email_verified=True,
                    last_login_at=timezone.now(),
                )
            else:
                user = identity.user
                cls._ensure_user_can_login(user)
                if identity.deleted_at is not None:
                    identity.deleted_at = None

            cls._sync_user_profile(
                User=User,
                user=user,
                email=email,
                full_name=full_name,
                avatar_url=avatar_url,
            )
            cls.ensure_default_student_role(user)
            cls._sync_identity(identity)

        return user

    @staticmethod
    def normalize_email(email: str) -> str:
        return email.strip().lower()

    @classmethod
    def ensure_default_student_role(cls, user) -> None:
        if UserRole.objects.filter(user=user).exists():
            return

        try:
            role = Role.objects.get(code=cls.DEFAULT_ROLE_CODE, is_active=True)
        except Role.DoesNotExist as exc:
            raise AuthenticationFailed("Default student role is not configured.") from exc

        existing = UserRole.all_objects.select_for_update().filter(user=user, role=role).first()
        if existing is not None:
            existing.deleted_at = None
            existing.is_primary = True
            existing.save(update_fields=["deleted_at", "is_primary", "updated_at"])
            return

        UserRole.objects.create(user=user, role=role, is_primary=True)

    @staticmethod
    def _require_subject(payload: dict[str, Any]) -> str:
        subject = str(payload.get("sub") or "").strip()
        if not subject:
            raise AuthenticationFailed("Token missing subject.")
        return subject

    @classmethod
    def _require_verified_email(cls, payload: dict[str, Any]) -> str:
        raw_email = str(payload.get("email") or "").strip()
        if not raw_email:
            raise AuthenticationFailed("Token missing email.")
        if payload.get("email_verified") is not True:
            raise AuthenticationFailed("Email is not verified.")
        return cls.normalize_email(raw_email)

    @staticmethod
    def _extract_full_name(payload: dict[str, Any]) -> str:
        if payload.get("name"):
            return str(payload["name"]).strip()

        given_name = str(payload.get("given_name") or "").strip()
        family_name = str(payload.get("family_name") or "").strip()
        return " ".join(part for part in [given_name, family_name] if part)

    @staticmethod
    def _extract_avatar_url(payload: dict[str, Any]) -> str:
        return str(payload.get("picture") or "").strip()

    @classmethod
    def _get_or_create_user_for_email(cls, *, User, email: str, full_name: str):
        users = list(
            User.objects.select_for_update()
            .filter(email__iexact=email)
            .order_by("id")[:2]
        )
        if len(users) > 1:
            raise AuthenticationFailed("Multiple local users use this email.")

        if users:
            user = users[0]
            cls._ensure_user_can_login(user)
            cls._ensure_username_available(User=User, email=email, user=user)
            return user

        cls._ensure_username_available(User=User, email=email, user=None)
        return User.objects.create_user(
            username=email,
            email=email,
            full_name=full_name,
        )

    @staticmethod
    def _ensure_user_can_login(user) -> None:
        if getattr(user, "deleted_at", None) is not None:
            raise AuthenticationFailed("User account is deleted.")
        if not user.is_active:
            raise AuthenticationFailed("User account is disabled.")
        if getattr(user, "account_status", None) == user.AccountStatus.BANNED:
            raise AuthenticationFailed("User account is banned.")

    @staticmethod
    def _ensure_username_available(*, User, email: str, user) -> None:
        qs = User.objects.select_for_update().filter(username__iexact=email)
        if user is not None:
            qs = qs.exclude(pk=user.pk)
        if qs.exists():
            raise AuthenticationFailed("A local user already uses this email as username.")

    @classmethod
    def _sync_user_profile(cls, *, User, user, email: str, full_name: str, avatar_url: str) -> None:
        cls._ensure_username_available(User=User, email=email, user=user)

        update_fields = []
        if user.username != email:
            user.username = email
            update_fields.append("username")
        if user.email != email:
            user.email = email
            update_fields.append("email")
        if full_name and user.full_name != full_name:
            user.full_name = full_name
            update_fields.append("full_name")
        if avatar_url and user.avatar_url != avatar_url:
            user.avatar_url = avatar_url
            update_fields.append("avatar_url")

        if update_fields:
            user.save(update_fields=[*update_fields, "updated_at"])

    @staticmethod
    def _sync_identity(identity: UserAuthIdentity) -> None:
        identity.deleted_at = None
        identity.email_verified = True
        identity.last_login_at = timezone.now()
        identity.save(update_fields=["deleted_at", "email_verified", "last_login_at", "updated_at"])
