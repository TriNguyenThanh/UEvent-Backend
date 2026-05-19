from typing import Any, Dict, Optional, Tuple

import jwt
from django.conf import settings
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed

from apps.users.services import KeycloakProvisioningService
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
        user = KeycloakProvisioningService.provision_from_payload(payload)
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
