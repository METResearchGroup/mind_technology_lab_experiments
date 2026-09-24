"""Load JSON fields from AWS Secrets Manager.

Run from the repository root:

    uv run python -c "from shared.aws.aws_region import AWS_REGION; print(AWS_REGION)"
"""

from __future__ import annotations

from typing import Protocol


class SecretsManagerClient(Protocol):
    """Minimal Secrets Manager client surface for tests."""

    def get_secret_value(self, SecretId: str) -> dict[str, str]:
        """Return a Secrets Manager GetSecretValue response."""
        ...


def secrets_manager_client() -> SecretsManagerClient:
    """Build a Secrets Manager client using the default credential chain."""
    raise NotImplementedError


def load_secret_field(
    secret_id: str, field_name: str, client: SecretsManagerClient
) -> str:
    """Read one JSON field from a Secrets Manager secret."""
    raise NotImplementedError
