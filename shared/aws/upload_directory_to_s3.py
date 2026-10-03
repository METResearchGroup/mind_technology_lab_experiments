"""Upload a local directory to S3.

Run from the repository root:

    uv run python -c "from shared.aws.upload_directory_to_s3 import parse_s3_uri; print(parse_s3_uri('s3://bucket/prefix'))"
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

import boto3

from shared.aws.constants import DEFAULT_REGION_NAME


def parse_s3_uri(uri: str) -> tuple[str, str]:
    """Split ``s3://bucket/prefix`` into a bucket and a key prefix.

    Parameters
    ----------
    uri
        Destination such as ``s3://mind-technology-lab-experiments/cookbooks/example``.

    Returns
    -------
    tuple[str, str]
        Bucket name and key prefix. The prefix has no leading or trailing slash.

    Raises
    ------
    ValueError
        When ``uri`` is not an ``s3://`` URI with a bucket name.
    """
    parsed = urlparse(uri)
    if parsed.scheme != "s3" or not parsed.netloc:
        raise ValueError(f"Invalid S3 URI: {uri}")
    prefix = parsed.path.lstrip("/").rstrip("/")
    return parsed.netloc, prefix


def upload_directory(
    local_dir: Path,
    s3_uri: str,
    *,
    region: str = DEFAULT_REGION_NAME,
) -> list[str]:
    """Upload every file under ``local_dir`` to ``s3_uri``.

    Parameters
    ----------
    local_dir
        Directory whose files are uploaded, including nested files.
    s3_uri
        Destination prefix ``s3://bucket/prefix``.
    region
        AWS region for the S3 client.

    Returns
    -------
    list[str]
        Uploaded object URIs, in sorted path order.

    Raises
    ------
    FileNotFoundError
        When ``local_dir`` is not a directory.
    RuntimeError
        When ``local_dir`` contains no files.
    """
    if not local_dir.is_dir():
        raise FileNotFoundError(f"Not a directory: {local_dir}")

    bucket, prefix = parse_s3_uri(s3_uri)
    client = boto3.client("s3", region_name=region)
    uploaded: list[str] = []
    for path in sorted(local_dir.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(local_dir).as_posix()
        key = f"{prefix}/{relative}" if prefix else relative
        client.upload_file(str(path), bucket, key)
        uri = f"s3://{bucket}/{key}"
        uploaded.append(uri)
        print(f"Uploaded {uri}")

    if not uploaded:
        raise RuntimeError(f"No files to upload in {local_dir}")
    return uploaded
