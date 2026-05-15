import json
import threading
from typing import Any, Dict, Optional

import jwt
import requests
from cachetools import TTLCache
from django.conf import settings

_JWKS_CACHE_KEY = "jwks"
_jwks_cache = TTLCache(maxsize=1, ttl=settings.KEYCLOAK_JWKS_CACHE_TTL)
_jwks_lock = threading.Lock()


def _fetch_jwks() -> Dict[str, Any]:
    try:
        response = requests.get(
            settings.KEYCLOAK_JWKS_URL,
            timeout=settings.KEYCLOAK_JWKS_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        raise ValueError("Failed to fetch JWKS.") from exc
    if "keys" not in data:
        raise ValueError("JWKS response missing 'keys'.")
    return data


def get_jwks(*, force_refresh: bool = False) -> Dict[str, Any]:
    """Return cached JWKS, fetching from Keycloak if needed."""
    if not force_refresh:
        cached = _jwks_cache.get(_JWKS_CACHE_KEY)
        if cached is not None:
            return cached

    with _jwks_lock:
        if not force_refresh:
            cached = _jwks_cache.get(_JWKS_CACHE_KEY)
            if cached is not None:
                return cached
        data = _fetch_jwks()
        _jwks_cache[_JWKS_CACHE_KEY] = data
        return data


def get_jwk_for_kid(kid: str) -> Optional[Dict[str, Any]]:
    """Find the JWK for a given kid, retrying once on cache miss."""
    jwks = get_jwks()
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return key

    jwks = get_jwks(force_refresh=True)
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return key

    return None


def build_rsa_public_key(jwk: Dict[str, Any]):
    """Build a cryptography public key from an RSA JWK."""
    if jwk.get("kty") != "RSA":
        raise ValueError("Unsupported JWK key type.")
    return jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(jwk))
