import hashlib
import time
from typing import Any, Dict, Optional, Tuple

import jwt
from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.cache import cache
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed

from apps.users.services import KeycloakProvisioningService
from common.keycloak import build_rsa_public_key, get_jwk_for_kid


class KeycloakJWTAuthentication(BaseAuthentication):
    """Authenticate requests using Keycloak-issued access tokens."""

    keyword = "Bearer"
    cache_key_prefix = "keycloak_auth_user"

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
        user = self._get_cached_user(token)
        if user is not None:
            return user, payload

        user = KeycloakProvisioningService.provision_from_payload(payload)
        self._cache_authenticated_user(token, payload, user)
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
                leeway=settings.KEYCLOAK_JWT_LEEWAY_SECONDS,
            )
        except jwt.ExpiredSignatureError as exc:
            raise AuthenticationFailed("Token has expired.") from exc
        except jwt.InvalidAudienceError as exc:
            raise AuthenticationFailed("Invalid token audience.") from exc
        except jwt.InvalidIssuerError as exc:
            raise AuthenticationFailed("Invalid token issuer.") from exc
        except jwt.PyJWTError as exc:
            raise AuthenticationFailed("Invalid token.") from exc

    def _get_cached_user(self, token: str):
        user_id = cache.get(self._cache_key(token))
        if user_id is None:
            return None

        User = get_user_model()
        try:
            user = User.objects.get(pk=user_id)
            KeycloakProvisioningService._ensure_user_can_login(user)
        except User.DoesNotExist as exc:
            cache.delete(self._cache_key(token))
            raise AuthenticationFailed("Cached token user is no longer valid.") from exc
        except AuthenticationFailed:
            cache.delete(self._cache_key(token))
            raise

        return user

    def _cache_authenticated_user(self, token: str, payload: Dict[str, Any], user) -> None:
        timeout = self._cache_timeout(payload)
        if timeout <= 0:
            return
        cache.set(self._cache_key(token), str(user.pk), timeout=timeout)

    def _cache_key(self, token: str) -> str:
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        return f"{self.cache_key_prefix}:{token_hash}"

    def _cache_timeout(self, payload: Dict[str, Any]) -> int:
        max_timeout = getattr(settings, "KEYCLOAK_AUTH_USER_CACHE_TTL", 300)
        exp = payload.get("exp")
        if exp is None:
            return max_timeout

        try:
            seconds_until_expiry = int(exp) - int(time.time())
        except (TypeError, ValueError):
            return max_timeout
        return min(max_timeout, seconds_until_expiry)
