"""Pick an ObjectStore from settings. Local in dev, S3 in deployed envs."""

from __future__ import annotations

from functools import lru_cache

from app.config import get_settings

from .base import ObjectStore
from .local import LocalObjectStore


@lru_cache
def get_object_store() -> ObjectStore:
    settings = get_settings()
    if settings.environment == "local":
        return LocalObjectStore(root="./_local_object_store")
    from .s3 import S3ObjectStore  # imported only when needed

    return S3ObjectStore(bucket=settings.s3_bucket_uploads, region=settings.aws_region)
