"""Private media storage abstraction.

Local disk is the development/default backend.  Set STORAGE_BACKEND=s3 plus the
S3_* variables to use any S3-compatible service (Cloudflare R2, AWS S3,
Backblaze B2, MinIO, etc.).  Objects remain private: Flask authorizes the user
first and then streams the bytes; no public bucket is required.
"""
from __future__ import annotations

import io
import os
from pathlib import Path

from flask import current_app


def backend() -> str:
    return (current_app.config.get("STORAGE_BACKEND") or "local").lower()


def _local_root() -> Path:
    configured = current_app.config.get("UPLOAD_ROOT")
    root = Path(configured) if configured else Path(current_app.instance_path) / "uploads"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _s3_client():
    import boto3
    endpoint = current_app.config.get("S3_ENDPOINT_URL") or None
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        region_name=current_app.config.get("S3_REGION") or "auto",
        aws_access_key_id=current_app.config.get("S3_ACCESS_KEY_ID"),
        aws_secret_access_key=current_app.config.get("S3_SECRET_ACCESS_KEY"),
    )


def _bucket() -> str:
    value = current_app.config.get("S3_BUCKET")
    if not value:
        raise RuntimeError("S3_BUCKET is required when STORAGE_BACKEND=s3")
    return value


def put_bytes(key: str, data: bytes, content_type: str | None = None) -> None:
    if backend() == "s3":
        kwargs = {"Bucket": _bucket(), "Key": key, "Body": data}
        if content_type:
            kwargs["ContentType"] = content_type
        _s3_client().put_object(**kwargs)
        return
    path = _local_root() / key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def get_bytes(key: str) -> bytes:
    if backend() == "s3":
        return _s3_client().get_object(Bucket=_bucket(), Key=key)["Body"].read()
    return (_local_root() / key).read_bytes()


def delete(key: str) -> None:
    if backend() == "s3":
        _s3_client().delete_object(Bucket=_bucket(), Key=key)
        return
    (_local_root() / key).unlink(missing_ok=True)


def exists(key: str) -> bool:
    if backend() == "s3":
        try:
            _s3_client().head_object(Bucket=_bucket(), Key=key)
            return True
        except Exception:
            return False
    return (_local_root() / key).exists()


def check_writable() -> None:
    key = ".nirmaan-healthcheck"
    put_bytes(key, b"ok", "text/plain")
    if get_bytes(key) != b"ok":
        raise RuntimeError("storage read-after-write check failed")
    delete(key)
