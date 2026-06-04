import hashlib
from typing import Any
from urllib.parse import urlencode

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed, ValidationError

from apps.users.models import Role, UserAuthIdentity, UserRole
from common import otp as otp_service
from common.keycloak_admin import update_keycloak_user_email


class UserService:
    """Business logic for mobile user operations."""

    @staticmethod
    def update_profile(user, validated_data: dict):
        """Update user profile fields from validated PATCH data."""
        update_fields = []

        for field_name in (
            "full_name",
            "phone_number",
            "student_code",
            "faculty",
            "class_name",
        ):
            if field_name in validated_data:
                setattr(user, field_name, validated_data[field_name])
                update_fields.append(field_name)

        if update_fields:
            with transaction.atomic():
                user.save(update_fields=update_fields)

        UserService.ensure_avatar_url(user)
        return user

    @staticmethod
    def ensure_avatar_url(user):
        """Persist a generated avatar once when the user has no avatar URL."""
        if (user.avatar_url or "").strip():
            return user

        user.avatar_url = UserService.build_generated_avatar_url(user)
        user.save(update_fields=["avatar_url", "updated_at"])
        return user

    @staticmethod
    def build_generated_avatar_url(user) -> str:
        display_name = (
            user.full_name
            or user.get_full_name()
            or user.username
            or user.email
            or "User"
        ).strip()
        seed = display_name.lower().encode("utf-8")
        background = hashlib.sha256(seed).hexdigest()[:6]
        initials = UserService._avatar_initials(display_name)
        params = urlencode(
            {
                "name": initials,
                "background": background,
                "color": "ffffff",
                "size": "256",
                "bold": "true",
                "format": "png",
            }
        )
        return f"https://ui-avatars.com/api/?{params}"

    @staticmethod
    def _avatar_initials(display_name: str) -> str:
        normalized = " ".join(display_name.split())
        parts = [part for part in normalized.split(" ") if part]
        if len(parts) >= 2:
            return "".join(part[0] for part in parts[:3]).upper()
        if parts:
            return parts[0][:2].upper()
        return "U"

    @staticmethod
    def send_email_change_otp(user) -> str:
        """Send an OTP to the user's current email before changing email."""
        current_email = KeycloakProvisioningService.normalize_email(user.email or "")
        if not current_email:
            raise ValidationError(
                {"email": "Tài khoản chưa có email hiện tại để xác nhận."}
            )

        otp_service.send_otp(current_email)
        return current_email

    @staticmethod
    def send_new_email_change_otp(
        user, *, new_email: str, current_otp_code: str
    ) -> str:
        """Verify the current-email OTP, then send an OTP to the requested new email."""
        User = get_user_model()
        current_email = KeycloakProvisioningService.normalize_email(user.email or "")
        normalized_email = KeycloakProvisioningService.normalize_email(new_email)

        UserService._validate_email_change_request(
            User=User,
            user=user,
            current_email=current_email,
            normalized_email=normalized_email,
        )
        UserService._verify_email_otp(
            email=current_email,
            otp_code=current_otp_code,
            consume=False,
            field_name="current_otp_code",
        )

        otp_service.send_otp(normalized_email)
        return normalized_email

    @staticmethod
    def change_email_with_otp(
        user,
        *,
        new_email: str,
        current_otp_code: str,
        new_email_otp_code: str,
        keycloak_subject: str = "",
    ):
        """Change user email after validating OTPs for current and new email."""
        User = get_user_model()
        current_email = KeycloakProvisioningService.normalize_email(user.email or "")
        normalized_email = KeycloakProvisioningService.normalize_email(new_email)

        UserService._validate_email_change_request(
            User=User,
            user=user,
            current_email=current_email,
            normalized_email=normalized_email,
        )

        with transaction.atomic():
            locked_user = User.objects.select_for_update().get(pk=user.pk)
            current_email = KeycloakProvisioningService.normalize_email(
                locked_user.email or ""
            )
            UserService._validate_email_change_request(
                User=User,
                user=locked_user,
                current_email=current_email,
                normalized_email=normalized_email,
            )
            UserService._verify_email_otp(
                email=current_email,
                otp_code=current_otp_code,
                consume=False,
                field_name="current_otp_code",
            )
            UserService._verify_email_otp(
                email=normalized_email,
                otp_code=new_email_otp_code,
                consume=False,
                field_name="new_email_otp_code",
            )

            identity = UserAuthIdentity.objects.select_for_update().filter(
                user=locked_user,
                provider=UserAuthIdentity.Provider.KEYCLOAK,
            )
            if keycloak_subject:
                identity = identity.filter(provider_subject=keycloak_subject)
            identity = identity.first()
            if identity is None:
                raise ValidationError(
                    {
                        "email": (
                            "Không tìm thấy danh tính đăng nhập để đồng bộ email. "
                            "Vui lòng đăng nhập lại và thử lại."
                        )
                    }
                )
            update_keycloak_user_email(identity.provider_subject, normalized_email)

            locked_user.email = normalized_email
            locked_user.username = normalized_email
            locked_user.save(update_fields=["email", "username", "updated_at"])
            otp_service.consume_otp(current_email)
            otp_service.consume_otp(normalized_email)

        return locked_user

    @staticmethod
    def _validate_email_change_request(
        *, User, user, current_email: str, normalized_email: str
    ) -> None:
        if not current_email:
            raise ValidationError(
                {"email": "Tài khoản chưa có email hiện tại để xác nhận."}
            )
        if normalized_email == current_email:
            raise ValidationError({"new_email": "Email mới phải khác email hiện tại."})

        if (
            User.objects.filter(email__iexact=normalized_email)
            .exclude(pk=user.pk)
            .exists()
        ):
            raise ValidationError(
                {"new_email": "Email này đã được sử dụng bởi tài khoản khác."}
            )

        username_conflict = (
            User.objects.filter(username__iexact=normalized_email)
            .exclude(pk=user.pk)
            .exists()
        )
        if username_conflict:
            raise ValidationError(
                {"new_email": "Email này đã được sử dụng bởi tài khoản khác."}
            )

    @staticmethod
    def _verify_email_otp(
        *,
        email: str,
        otp_code: str,
        consume: bool,
        field_name: str,
    ) -> None:
        try:
            otp_service.verify_otp(email, otp_code, consume=consume)
        except otp_service.OtpExpiredError as exc:
            raise ValidationError({field_name: str(exc)}) from exc
        except otp_service.OtpInvalidError as exc:
            raise ValidationError({field_name: str(exc)}) from exc
        except otp_service.OtpMaxAttemptsError as exc:
            raise ValidationError({field_name: str(exc)}) from exc


class KeycloakProvisioningService:
    """Provision and sync local users from validated Keycloak JWT payloads."""

    DEFAULT_ROLE_CODE = "student"
    REALM_ROLE_CODE_MAP = {
        "student": ("student", "ATTENDEE"),
        "organizer": ("organizer", "ORGANIZER"),
        "super_admin": ("system_admin", "SYS_ADMIN", "admin"),
    }
    SUPER_ADMIN_REALM_ROLE = "super_admin"

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
            cls.sync_roles_from_payload(user=user, payload=payload)
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
            raise AuthenticationFailed(
                "Default student role is not configured."
            ) from exc

        existing = (
            UserRole.all_objects.select_for_update()
            .filter(user=user, role=role)
            .first()
        )
        if existing is not None:
            existing.deleted_at = None
            existing.is_primary = True
            existing.save(update_fields=["deleted_at", "is_primary", "updated_at"])
            return

        UserRole.objects.create(user=user, role=role, is_primary=True)

    @classmethod
    def sync_roles_from_payload(cls, *, user, payload: dict[str, Any]) -> None:
        realm_roles = cls._extract_realm_roles(payload)
        role_codes = cls._map_realm_roles_to_local_codes(realm_roles)

        if role_codes:
            cls._ensure_user_roles(user=user, role_codes=role_codes)
        else:
            cls.ensure_default_student_role(user)

        if cls.SUPER_ADMIN_REALM_ROLE in realm_roles:
            cls._ensure_superuser_flags(user)

    @staticmethod
    def _extract_realm_roles(payload: dict[str, Any]) -> set[str]:
        realm_access = payload.get("realm_access")
        if not isinstance(realm_access, dict):
            return set()

        roles = realm_access.get("roles")
        if not isinstance(roles, list):
            return set()

        return {str(role).strip() for role in roles if str(role).strip()}

    @classmethod
    def _map_realm_roles_to_local_codes(cls, realm_roles: set[str]) -> list[str]:
        role_codes = []
        seen = set()

        for realm_role, candidates in cls.REALM_ROLE_CODE_MAP.items():
            if realm_role not in realm_roles:
                continue

            role = None
            for candidate in candidates:
                role = Role.objects.filter(code=candidate, is_active=True).first()
                if role is not None:
                    break
            if role is not None and role.code not in seen:
                role_codes.append(role.code)
                seen.add(role.code)

        return role_codes

    @staticmethod
    def _ensure_user_roles(*, user, role_codes: list[str]) -> None:
        existing_roles = {
            user_role.role.code: user_role
            for user_role in UserRole.all_objects.select_for_update()
            .select_related("role")
            .filter(user=user, role__code__in=role_codes)
        }
        has_primary_role = UserRole.objects.filter(user=user, is_primary=True).exists()

        for role_code in role_codes:
            role = Role.objects.get(code=role_code, is_active=True)
            user_role = existing_roles.get(role_code)
            is_primary = not has_primary_role

            if user_role is None:
                UserRole.objects.create(user=user, role=role, is_primary=is_primary)
                has_primary_role = True
                continue

            update_fields = []
            if user_role.deleted_at is not None:
                user_role.deleted_at = None
                update_fields.append("deleted_at")
            if is_primary and not user_role.is_primary:
                user_role.is_primary = True
                update_fields.append("is_primary")
                has_primary_role = True
            if update_fields:
                user_role.save(update_fields=[*update_fields, "updated_at"])

    @staticmethod
    def _ensure_superuser_flags(user) -> None:
        update_fields = []
        if not user.is_superuser:
            user.is_superuser = True
            update_fields.append("is_superuser")
        if not user.is_staff:
            user.is_staff = True
            update_fields.append("is_staff")
        if update_fields:
            user.save(update_fields=[*update_fields, "updated_at"])

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
            raise AuthenticationFailed(
                "A local user already uses this email as username."
            )

    @classmethod
    def _sync_user_profile(
        cls, *, User, user, email: str, full_name: str, avatar_url: str
    ) -> None:
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
        elif not (user.avatar_url or "").strip():
            user.avatar_url = UserService.build_generated_avatar_url(user)
            update_fields.append("avatar_url")

        if update_fields:
            user.save(update_fields=[*update_fields, "updated_at"])

    @staticmethod
    def _sync_identity(identity: UserAuthIdentity) -> None:
        identity.deleted_at = None
        identity.email_verified = True
        identity.last_login_at = timezone.now()
        identity.save(
            update_fields=[
                "deleted_at",
                "email_verified",
                "last_login_at",
                "updated_at",
            ]
        )
