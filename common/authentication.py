from typing import Any, Dict, Optional, Tuple

import jwt
# pyrefly: ignore [missing-import]
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed

from apps.users.models import UserAuthIdentity
from common.keycloak import build_rsa_public_key, get_jwk_for_kid


class KeycloakJWTAuthentication(BaseAuthentication):
    """Authenticate requests using Keycloak-issued access tokens."""

    keyword = "Bearer"

    def authenticate(self, request) -> Optional[Tuple[Any, Dict[str, Any]]]:
        token = self._get_bearer_token(request)
        if token is None:
            return None

        try:
            return self.authenticate_token(token)
        except AuthenticationFailed as e:
            print(f"[Keycloak Auth Error] {e}")
            raise

    def authenticate_token(self, token: str) -> Tuple[Any, Dict[str, Any]]:
        payload = self._decode_token(token)
        user = self._get_or_create_user(payload)
        return user, payload

    def authenticate_header(self, request) -> str:
        return self.keyword

    def _get_bearer_token(self, request) -> Optional[str]:
        auth = get_authorization_header(request).split()
        if not auth:
            return None

        if auth[0].lower() != self.keyword.lower().encode():
            return None

        if len(auth) == 1:
            raise AuthenticationFailed("Invalid Authorization header. No credentials provided.")
        if len(auth) > 2:
            raise AuthenticationFailed("Invalid Authorization header. Credentials string should not contain spaces.")

        return auth[1].decode("utf-8")

    def _decode_token(self, token: str) -> Dict[str, Any]:
        try:
            header = jwt.get_unverified_header(token)
        except jwt.PyJWTError as exc:
            raise AuthenticationFailed("Invalid token header.") from exc

        kid = header.get("kid")
        if not kid:
            raise AuthenticationFailed("Token missing key id.")

        alg = header.get("alg")
        if alg and alg not in settings.KEYCLOAK_JWT_ALGORITHMS:
            raise AuthenticationFailed("Unsupported token algorithm.")

        try:
            jwk = get_jwk_for_kid(kid)
        except ValueError as exc:
            raise AuthenticationFailed("Unable to fetch JWKS.") from exc
        if jwk is None:
            raise AuthenticationFailed("No matching public key for token.")

        try:
            public_key = build_rsa_public_key(jwk)
        except ValueError as exc:
            raise AuthenticationFailed("Unsupported public key type.") from exc

        try:
            return jwt.decode(
                token,
                key=public_key,
                algorithms=settings.KEYCLOAK_JWT_ALGORITHMS,
                issuer=settings.KEYCLOAK_ISSUER,
                audience=settings.KEYCLOAK_AUDIENCE,
            )
        except jwt.ExpiredSignatureError as exc:
            raise AuthenticationFailed("Token has expired.") from exc
        except jwt.InvalidAudienceError as exc:
            raise AuthenticationFailed("Invalid token audience.") from exc
        except jwt.InvalidIssuerError as exc:
            raise AuthenticationFailed("Invalid token issuer.") from exc
        except jwt.PyJWTError as exc:
            raise AuthenticationFailed("Invalid token.") from exc

    def _get_or_create_user(self, payload: Dict[str, Any]):
        subject = payload.get("sub")
        if not subject:
            raise AuthenticationFailed("Token missing subject.")

        email = payload.get("email")
        email_verified = bool(payload.get("email_verified", False))
        full_name, has_name = self._extract_full_name(payload)
        avatar_url, has_avatar = self._extract_avatar_url(payload)
        has_email = "email" in payload

        User = get_user_model()

        with transaction.atomic():
            identity = UserAuthIdentity.objects.select_related("user").filter(
                provider=UserAuthIdentity.Provider.KEYCLOAK,
                provider_subject=subject,
            ).first()

            if identity is None:
                user = None
                if email:
                    user = User.objects.filter(email__iexact=email).first()
                    if user and not email_verified:
                        raise AuthenticationFailed("Email is not verified.")
                    if user and not user.is_active:
                        raise AuthenticationFailed("User account is disabled.")

                if user is None:
                    user = User.objects.create_user(
                        username=subject,
                        email=email or "",
                        full_name=full_name or "",
                    )

                identity = UserAuthIdentity.objects.create(
                    user=user,
                    provider=UserAuthIdentity.Provider.KEYCLOAK,
                    provider_subject=subject,
                    email_verified=email_verified,
                    last_login_at=timezone.now(),
                )
            else:
                user = identity.user
                if not user.is_active:
                    raise AuthenticationFailed("User account is disabled.")

            self._sync_user_profile(
                user,
                email=email,
                has_email=has_email,
                full_name=full_name,
                has_name=has_name,
                avatar_url=avatar_url,
                has_avatar=has_avatar,
            )
            self._sync_identity(identity, email_verified=email_verified)

        return user

    def _extract_full_name(self, payload: Dict[str, Any]) -> Tuple[Optional[str], bool]:
        if "name" in payload and payload.get("name"):
            return payload.get("name"), True

        given_name = payload.get("given_name")
        family_name = payload.get("family_name")
        if given_name or family_name:
            return " ".join(part for part in [given_name, family_name] if part), True

        return None, False

    def _extract_avatar_url(self, payload: Dict[str, Any]) -> Tuple[Optional[str], bool]:
        if "picture" in payload:
            return payload.get("picture"), True
        return None, False

    def _sync_user_profile(
        self,
        user,
        *,
        email: Optional[str],
        has_email: bool,
        full_name: Optional[str],
        has_name: bool,
        avatar_url: Optional[str],
        has_avatar: bool,
    ) -> None:
        update_fields = []

        if has_email and email is not None and user.email != email:
            user.email = email
            update_fields.append("email")

        if has_name and full_name is not None and user.full_name != full_name:
            user.full_name = full_name
            update_fields.append("full_name")

        if has_avatar and user.avatar_url != (avatar_url or ""):
            user.avatar_url = avatar_url or ""
            update_fields.append("avatar_url")

        if update_fields:
            user.save(update_fields=update_fields)

    def _sync_identity(self, identity: UserAuthIdentity, *, email_verified: bool) -> None:
        identity.email_verified = email_verified
        identity.last_login_at = timezone.now()
        identity.save(update_fields=["email_verified", "last_login_at"])
