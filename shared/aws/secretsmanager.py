# ruff: noqa: E501
"""Load JSON fields from AWS Secrets Manager.

Run from the repository root:

    uv run python -c "from shared.aws.secretsmanager import secrets_manager_client; print(secrets_manager_client().__class__.__name__)"
"""

from __future__ import annotations

import json
from typing import Protocol, cast

import boto3
from botocore.exceptions import ClientError

from shared.aws.aws_region import AWS_REGION


class SecretsManagerClient(Protocol):
    """Minimal Secrets Manager client surface for tests."""

    def get_secret_value(self, SecretId: str) -> dict[str, str]:
        """Return a Secrets Manager GetSecretValue response.

        Parameters
        ----------
        SecretId
            Secrets Manager secret name or ARN.

        Returns
        -------
        dict[str, str]
            Boto3 response payload (includes ``SecretString`` when present).
        """
        ...


def secrets_manager_client() -> SecretsManagerClient:
    """Build a Secrets Manager client using the default credential chain.

    Returns
    -------
    SecretsManagerClient
        Boto3 Secrets Manager client for :data:`shared.aws.aws_region.AWS_REGION`.
    """
    return cast(
        SecretsManagerClient,
        boto3.client("secretsmanager", region_name=AWS_REGION),
    )


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
    field_value = payload.get(field_name)
    if not field_value:
        raise SystemExit(f"Secret {secret_id} is missing {field_name}.")
    return field_value


def _read_secret_string(secret_id: str, client: SecretsManagerClient) -> str:
    """Fetch the SecretString for ``secret_id`` or exit with a clear message."""
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
    """Parse ``secret_string`` as a JSON object or exit on invalid payload."""
    try:
        payload = json.loads(secret_string)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Secret {secret_id} is not valid JSON.") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"Secret {secret_id} is not a JSON object.")
    return payload
