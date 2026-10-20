"""Load API keys from AWS Secrets Manager in us-east-2.

Run from the experiment folder:

    uv run python -m shared.secrets
"""

from __future__ import annotations

import json
import os
from typing import Protocol

import boto3
from botocore.exceptions import ClientError

AWS_REGION = "us-east-2"
TYPESAFE_SECRET_ID = "jev-typesafe-api-key"
TYPESAFE_FIELD_NAME = "TYPESAFE_API_KEY"
HF_SECRET_ID = "hf-token"
CLOUDFLARE_SECRET_ID = "cloudflare-workers-ai"
LAB_ACCESS_KEY_ID_ENV = "LAB_AWS_ACCESS_KEY_ID"
LAB_SECRET_ACCESS_KEY_ENV = "LAB_AWS_ACCESS_KEY_SECRET"
ACCESS_KEY_ID_ENV = "AWS_ACCESS_KEY_ID"
SECRET_ACCESS_KEY_ENV = "AWS_SECRET_ACCESS_KEY"
ACCESS_KEY_SECRET_ENV = "AWS_ACCESS_KEY_SECRET"


class SecretsManagerClient(Protocol):
    """Minimal Secrets Manager client surface."""

    def get_secret_value(self, SecretId: str) -> dict[str, str]:
        """Return a Secrets Manager GetSecretValue response."""


def resolve_aws_access_keys() -> tuple[str, str]:
    """Resolve lab AWS keys, then standard environment names."""
    lab_id = os.environ.get(LAB_ACCESS_KEY_ID_ENV, "")
    lab_secret = os.environ.get(LAB_SECRET_ACCESS_KEY_ENV, "")
    if lab_id and lab_secret:
        return lab_id, lab_secret
    access_key_id = os.environ.get(ACCESS_KEY_ID_ENV, "")
    secret_access_key = os.environ.get(SECRET_ACCESS_KEY_ENV, "")
    if not secret_access_key:
        secret_access_key = os.environ.get(ACCESS_KEY_SECRET_ENV, "")
    return access_key_id, secret_access_key


def build_boto3_session() -> boto3.session.Session:
    """Build a boto3 session pinned to us-east-2."""
    access_key_id, secret_access_key = resolve_aws_access_keys()
    session_kwargs: dict[str, str] = {"region_name": AWS_REGION}
    if access_key_id and secret_access_key:
        session_kwargs["aws_access_key_id"] = access_key_id
        session_kwargs["aws_secret_access_key"] = secret_access_key
    return boto3.session.Session(**session_kwargs)


def _secrets_client() -> SecretsManagerClient:
    session = build_boto3_session()
    return session.client("secretsmanager", region_name=AWS_REGION)


def _read_secret_string(secret_id: str, client: SecretsManagerClient) -> str:
    try:
        response = client.get_secret_value(SecretId=secret_id)
    except ClientError as exc:
        raise SystemExit(
            f"Could not load {secret_id} from Secrets Manager: {exc}"
        ) from exc
    secret_string = response.get("SecretString")
    if not secret_string:
        raise SystemExit(f"Secret {secret_id} has no SecretString.")
    return secret_string


def _parse_secret_json(secret_id: str, secret_string: str) -> dict[str, str]:
    try:
        payload = json.loads(secret_string)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Secret {secret_id} is not valid JSON.") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"Secret {secret_id} is not a JSON object.")
    return payload


def load_secret_field(
    secret_id: str, field_name: str, client: SecretsManagerClient | None = None
) -> str:
    """Read one JSON field from a Secrets Manager secret."""
    sm = client or _secrets_client()
    secret_string = _read_secret_string(secret_id, sm)
    payload = _parse_secret_json(secret_id, secret_string)
    value = payload.get(field_name)
    if not value:
        raise SystemExit(f"Secret {secret_id} is missing {field_name}.")
    return str(value)


def load_typesafe_api_key() -> str:
    """Load TYPESAFE_API_KEY from secret jev-typesafe-api-key."""
    return load_secret_field(TYPESAFE_SECRET_ID, TYPESAFE_FIELD_NAME)


def load_hf_token() -> str:
    """Load the Hugging Face token from secret hf-token."""
    secret_string = _read_secret_string(HF_SECRET_ID, _secrets_client())
    stripped = secret_string.strip()
    if not stripped.startswith("{"):
        return stripped
    payload = _parse_secret_json(HF_SECRET_ID, secret_string)
    for key in ("HF_TOKEN", "token", "huggingface_token"):
        if payload.get(key):
            return str(payload[key])
    raise SystemExit(f"Secret {HF_SECRET_ID} has no recognized token field.")


def load_cloudflare_workers_ai() -> tuple[str, str]:
    """Return Cloudflare account_id and api_token."""
    sm = _secrets_client()
    account_id = load_secret_field(CLOUDFLARE_SECRET_ID, "account_id", sm)
    api_token = load_secret_field(CLOUDFLARE_SECRET_ID, "api_token", sm)
    return account_id, api_token


def main() -> None:
    """Print ok lines for configured secrets without revealing values."""
    load_typesafe_api_key()
    print(f"ok {TYPESAFE_SECRET_ID}")
    load_hf_token()
    print(f"ok {HF_SECRET_ID}")
    load_cloudflare_workers_ai()
    print(f"ok {CLOUDFLARE_SECRET_ID}")


if __name__ == "__main__":
    main()
