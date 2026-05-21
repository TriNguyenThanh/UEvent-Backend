from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import BinaryIO
from urllib.parse import quote

import boto3
from botocore.config import Config
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


@dataclass(frozen=True)
class S3UploadResult:
    key: str
    bucket: str
    url: str
    etag: str | None = None


class S3Client:
    """Small wrapper around boto3 for application file uploads."""

    def __init__(self, bucket_name: str | None = None):
        self.bucket_name = bucket_name or settings.AWS_STORAGE_BUCKET_NAME
        if not self.bucket_name:
            raise ImproperlyConfigured("AWS_STORAGE_BUCKET_NAME is required to use S3Client.")

        client_kwargs = {
            "config": Config(
                signature_version="s3v4",
                s3={"addressing_style": "virtual"},
            ),
            "endpoint_url": self._get_endpoint_url(),
            "region_name": settings.AWS_S3_REGION_NAME,
        }
        if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
            client_kwargs["aws_access_key_id"] = settings.AWS_ACCESS_KEY_ID
            client_kwargs["aws_secret_access_key"] = settings.AWS_SECRET_ACCESS_KEY

        self.client = boto3.client("s3", **client_kwargs)

    def upload_fileobj(
        self,
        fileobj: BinaryIO,
        key: str,
        *,
        content_type: str | None = None,
        extra_args: dict | None = None,
    ) -> S3UploadResult:
        clean_key = self._normalize_key(key)
        args = self._build_upload_args(content_type=content_type, extra_args=extra_args)

        response = self.client.put_object(
            Bucket=self.bucket_name,
            Key=clean_key,
            Body=fileobj,
            **args,
        )

        return S3UploadResult(
            key=clean_key,
            bucket=self.bucket_name,
            url=self.build_url(clean_key),
            etag=response.get("ETag", "").strip('"') or None,
        )

    def upload_bytes(
        self,
        data: bytes,
        key: str,
        *,
        content_type: str | None = None,
        extra_args: dict | None = None,
    ) -> S3UploadResult:
        return self.upload_fileobj(
            BytesIO(data),
            key,
            content_type=content_type,
            extra_args=extra_args,
        )

    def generate_presigned_url(
        self,
        key: str,
        *,
        expires_in: int | None = None,
        method: str = "get_object",
        params: dict | None = None,
    ) -> str:
        clean_key = self._normalize_key(key)
        request_params = {"Bucket": self.bucket_name, "Key": clean_key}
        if params:
            request_params.update(params)

        return self.client.generate_presigned_url(
            method,
            Params=request_params,
            ExpiresIn=expires_in or settings.AWS_S3_PRESIGNED_URL_EXPIRES,
        )

    def delete_object(self, key: str) -> None:
        clean_key = self._normalize_key(key)
        self.client.delete_object(Bucket=self.bucket_name, Key=clean_key)

    def build_url(self, key: str) -> str:
        clean_key = self._normalize_key(key)
        encoded_key = quote(clean_key, safe="/")
        if settings.AWS_S3_CUSTOM_DOMAIN:
            return f"https://{settings.AWS_S3_CUSTOM_DOMAIN.rstrip('/')}/{encoded_key}"
        if self._uses_default_aws_endpoint():
            return (
                f"https://{self.bucket_name}.s3."
                f"{settings.AWS_S3_REGION_NAME}.amazonaws.com/{encoded_key}"
            )

        endpoint = self._get_endpoint_url().rstrip("/")
        return f"{endpoint}/{self.bucket_name}/{encoded_key}"

    @staticmethod
    def _uses_default_aws_endpoint() -> bool:
        endpoint_url = settings.AWS_S3_ENDPOINT_URL.strip().rstrip("/")
        return endpoint_url in {
            "",
            "https://s3.amazonaws.com",
            "http://s3.amazonaws.com",
            f"https://s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com",
            f"http://s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com",
        }

    @staticmethod
    def _normalize_key(key: str) -> str:
        clean_key = key.strip().lstrip("/")
        if not clean_key:
            raise ValueError("S3 object key must not be empty.")
        return clean_key

    @staticmethod
    def _get_endpoint_url() -> str:
        endpoint_url = settings.AWS_S3_ENDPOINT_URL.strip().rstrip("/")
        if endpoint_url and endpoint_url not in {
            "https://s3.amazonaws.com",
            "http://s3.amazonaws.com",
        }:
            return endpoint_url
        return f"https://s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com"

    @staticmethod
    def _build_upload_args(
        *,
        content_type: str | None,
        extra_args: dict | None,
    ) -> dict:
        args = dict(settings.AWS_S3_OBJECT_PARAMETERS)
        if content_type:
            args["ContentType"] = content_type
        if extra_args:
            args.update(extra_args)
        return args
