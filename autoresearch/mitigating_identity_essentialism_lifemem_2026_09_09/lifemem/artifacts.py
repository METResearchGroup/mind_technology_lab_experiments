from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

DEFAULT_BUCKET = "mind-technology-lab-experiments"
DEFAULT_PREFIX = "autoresearch/mitigating_identity_essentialism_lifemem_2026_09_09/"
DEFAULT_RESULTS_REPO = "mtorres98/lifemem-replication-2026-09-09"
DEFAULT_SRC_REPO = "mtorres98/lifemem-replication-src"


def aws_credentials() -> tuple[str | None, str | None]:
    key = os.environ.get("AWS_ACCESS_KEY_ID") or os.environ.get("LAB_AWS_ACCESS_KEY_ID")
    secret = (
        os.environ.get("AWS_SECRET_ACCESS_KEY")
        or os.environ.get("AWS_ACCESS_KEY_SECRET")
        or os.environ.get("LAB_AWS_ACCESS_KEY_SECRET")
    )
    return key, secret


def push_json(data: dict[str, Any], filename: str, local_path: Path) -> dict[str, str]:
    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_text(
        json.dumps(data, indent=2, default=_json_default), encoding="utf-8"
    )
    urls: dict[str, str] = {"local": str(local_path)}
    hub = _push_hub(local_path, filename)
    if hub:
        urls["hub"] = hub
    s3 = _push_s3(local_path, filename)
    if s3:
        urls["s3"] = s3
    return urls


def _push_hub(path: Path, filename: str) -> str | None:
    token = os.environ.get("HF_TOKEN")
    if not token:
        return None
    from huggingface_hub import HfApi

    api = HfApi(token=token)
    username = os.environ.get("HF_USERNAME") or api.whoami()["name"]
    repo_id = (
        os.environ.get("LIFEMEM_RESULTS_REPO")
        or f"{username}/lifemem-replication-2026-09-09"
    )
    api.create_repo(repo_id, repo_type="dataset", exist_ok=True, private=False)
    api.upload_file(
        path_or_fileobj=str(path),
        path_in_repo=filename,
        repo_id=repo_id,
        repo_type="dataset",
    )
    return f"https://huggingface.co/datasets/{repo_id}/blob/main/{filename}"


def _push_s3(path: Path, filename: str) -> str | None:
    key, secret = aws_credentials()
    if not key or not secret:
        return None
    try:
        import boto3
    except ImportError:
        return None
    region = (
        os.environ.get("AWS_DEFAULT_REGION")
        or os.environ.get("AWS_REGION")
        or "us-east-1"
    )
    client = boto3.client(
        "s3",
        aws_access_key_id=key,
        aws_secret_access_key=secret,
        region_name=region,
    )
    bucket = os.environ.get("LIFEMEM_S3_BUCKET", DEFAULT_BUCKET)
    prefix = os.environ.get("LIFEMEM_S3_PREFIX", DEFAULT_PREFIX).rstrip("/") + "/"
    object_key = f"{prefix}{filename}"
    client.upload_file(str(path), bucket, object_key)
    return f"s3://{bucket}/{object_key}"


def _json_default(value: Any) -> Any:
    if hasattr(value, "item"):
        return value.item()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")
