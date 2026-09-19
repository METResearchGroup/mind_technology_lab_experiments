"""Load TypeSafe and Google API keys from Secrets Manager in us-east-2.

Run from the experiment folder:

    uv run python -m shared.secrets
"""

from __future__ import annotations

import json
import os
from typing import Protocol

import boto3
from botocore.exceptions import ClientError

from shared.aws_region import AWS_REGION

TYPESAFE_SECRET_ID = "jev-typesafe-api-key"
TYPESAFE_FIELD_NAME = "TYPESAFE_API_KEY"
GOOGLE_SECRET_ID = "google-api-key"
GOOGLE_FIELD_NAME = "GOOGLE_API_KEY"
LAB_ACCESS_KEY_ID_ENV = "LAB_AWS_ACCESS_KEY_ID"
LAB_SECRET_ACCESS_KEY_ENV = "LAB_AWS_ACCESS_KEY_SECRET"
ACCESS_KEY_ID_ENV = "AWS_ACCESS_KEY_ID"
SECRET_ACCESS_KEY_ENV = "AWS_SECRET_ACCESS_KEY"
ACCESS_KEY_SECRET_ENV = "AWS_ACCESS_KEY_SECRET"


class SecretsManagerClient(Protocol):
    def get_secret_value(self, SecretId: str) -> dict[str, str]:
        """Return a Secrets Manager GetSecretValue response."""


def resolve_aws_access_keys() -> tuple[str, str]:
    """Resolve lab AWS keys, then the standard names, then AWS_ACCESS_KEY_SECRET."""
    lab_access_key_id = os.environ.get(LAB_ACCESS_KEY_ID_ENV, "")
    lab_secret_access_key = os.environ.get(LAB_SECRET_ACCESS_KEY_ENV, "")
    if lab_access_key_id and lab_secret_access_key:
        return lab_access_key_id, lab_secret_access_key
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


def load_secret_field(
    secret_id: str, field_name: str, client: SecretsManagerClient
) -> str:
    """Read one JSON field from a Secrets Manager secret.

    Parameters
    ----------
    secret_id
        Secrets Manager secret name.
    field_name
        JSON key inside SecretString.
    client
        Secrets Manager client or test double.

    Returns
    -------
    str
        Field value. Never printed.

    Raises
    ------
    SystemExit
        When the secret or field is missing. The message names the secret.
    """
    secret_string = _read_secret_string(secret_id, client)
    payload = _parse_secret_json(secret_id, secret_string)
    api_key = payload.get(field_name)
    if not api_key:
        raise SystemExit(f"Secret {secret_id} is missing {field_name}.")
    return api_key


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


def load_typesafe_api_key() -> str:
    """Load TYPESAFE_API_KEY from secret jev-typesafe-api-key."""
    return load_secret_field(TYPESAFE_SECRET_ID, TYPESAFE_FIELD_NAME, _secrets_client())


def load_google_api_key() -> str:
    """Load GOOGLE_API_KEY from secret google-api-key."""
    return load_secret_field(GOOGLE_SECRET_ID, GOOGLE_FIELD_NAME, _secrets_client())


def load_api_keys() -> tuple[str, str]:
    """Load TypeSafe and Google keys. Never print the values."""
    return load_typesafe_api_key(), load_google_api_key()


def main() -> None:
    """Print ok lines for each secret name. Do not print key material."""
    load_typesafe_api_key()
    print(f"ok {TYPESAFE_SECRET_ID}")
    load_google_api_key()
    print(f"ok {GOOGLE_SECRET_ID}")


if __name__ == "__main__":
    main()
