import hashlib

from django.conf import settings
from django.core.cache import cache

from apps.users.services import UserService
from apps.utils.s3 import S3Client


def get_user_avatar_url(user) -> str:
    object_key = (getattr(user, "avatar_image_key", "") or "").strip()
    if object_key:
        return _avatar_image_url(object_key)

    avatar_url = (getattr(user, "avatar_url", "") or "").strip()
    if avatar_url:
        return avatar_url

    return UserService.build_generated_avatar_url(user)


def get_user_avatar_cache_key(user) -> str:
    object_key = (getattr(user, "avatar_image_key", "") or "").strip()
    if object_key:
        return _stable_image_cache_key("user-avatar:s3", object_key)

    avatar_url = (getattr(user, "avatar_url", "") or "").strip()
    if avatar_url:
        return _stable_image_cache_key("user-avatar:url", avatar_url)

    seed = f"{getattr(user, 'id', '')}:{getattr(user, 'full_name', '')}:{getattr(user, 'email', '')}"
    return _stable_image_cache_key("user-avatar:generated", seed)


def _avatar_image_url(object_key: str) -> str:
    cache_key = _presigned_avatar_url_cache_key(object_key)
    cached_url = cache.get(cache_key)
    if cached_url:
        return cached_url

    expires_in = settings.AWS_S3_PRESIGNED_URL_EXPIRES
    presigned_url = S3Client().generate_presigned_url(
        object_key,
        method="get_object",
        expires_in=expires_in,
    )
    cache_timeout = _presigned_avatar_url_cache_timeout(expires_in)
    if cache_timeout > 0:
        cache.set(cache_key, presigned_url, timeout=cache_timeout)
    return presigned_url


def _presigned_avatar_url_cache_key(object_key: str) -> str:
    digest = hashlib.sha256(object_key.encode("utf-8")).hexdigest()
    return (
        "users:avatar_image_url:v1:"
        f"{settings.AWS_S3_PRESIGNED_URL_EXPIRES}:{digest}"
    )


def _presigned_avatar_url_cache_timeout(expires_in: int) -> int:
    configured_timeout = settings.AWS_S3_PRESIGNED_GET_URL_CACHE_TTL
    safe_timeout = max(0, expires_in - 60)
    return min(configured_timeout, safe_timeout)


def _stable_image_cache_key(namespace: str, value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return f"{namespace}:{digest}"
