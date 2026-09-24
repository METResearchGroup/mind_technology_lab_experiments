"""Unit tests for shared.aws.secretsmanager."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from botocore.exceptions import ClientError

from shared.aws.secretsmanager import (
    SecretsManagerClient,
    load_secret_field,
    secrets_manager_client,
)


class FakeSecretsManagerClient:
    """Test double implementing SecretsManagerClient."""

    def __init__(
        self,
        *,
        secret_string: str | None = None,
        error: ClientError | None = None,
    ) -> None:
        self.secret_string = secret_string
        self.error = error
        self.secret_ids: list[str] = []

    def get_secret_value(self, SecretId: str) -> dict[str, str]:
        self.secret_ids.append(SecretId)
        if self.error is not None:
            raise self.error
        if self.secret_string is None:
            return {}
        return {"SecretString": self.secret_string}


def _client_error(secret_id: str) -> ClientError:
    return ClientError(
        error_response={
            "Error": {"Code": "ResourceNotFoundException", "Message": "not found"}
        },
        operation_name="GetSecretValue",
    )


class TestSecretsManagerClientFactory:
    """Tests for secrets_manager_client."""

    def test_builds_client_with_us_east_2_region(self) -> None:
        """Verifies boto3.client is called with secretsmanager and us-east-2."""
        with patch("shared.aws.secretsmanager.boto3.client") as mock_boto_client:
            mock_boto_client.return_value = object()

            secrets_manager_client()

            mock_boto_client.assert_called_once_with(
                "secretsmanager",
                region_name="us-east-2",
            )


class TestLoadSecretField:
    """Tests for load_secret_field."""

    def test_returns_field_value_from_json_secret(self) -> None:
        """Verifies a non-empty JSON field is returned."""
        secret_id = "kova-github-pat"
        field_name = "GITHUB_PAT_TOKEN"
        expected = "ghp_test_value"
        client = FakeSecretsManagerClient(
            secret_string=f'{{"{field_name}": "{expected}"}}',
        )

        result = load_secret_field(secret_id, field_name, client)

        assert result == expected
        assert client.secret_ids == [secret_id]

    def test_exits_when_field_is_missing(self) -> None:
        """Verifies missing fields raise SystemExit naming the secret and field."""
        secret_id = "kova-github-pat"
        field_name = "GITHUB_PAT_TOKEN"
        client = FakeSecretsManagerClient(secret_string="{}")

        with pytest.raises(SystemExit) as exc_info:
            load_secret_field(secret_id, field_name, client)

        message = str(exc_info.value)
        assert secret_id in message
        assert field_name in message
        assert "ghp_test_value" not in message

    def test_exits_when_secret_string_is_not_json(self) -> None:
        """Verifies invalid JSON raises SystemExit with invalid JSON message."""
        secret_id = "kova-github-pat"
        field_name = "GITHUB_PAT_TOKEN"
        client = FakeSecretsManagerClient(secret_string="not-json")

        with pytest.raises(SystemExit) as exc_info:
            load_secret_field(secret_id, field_name, client)

        message = str(exc_info.value)
        assert message == f"Secret {secret_id} is not valid JSON."

    def test_exits_when_get_secret_value_raises_client_error(self) -> None:
        """Verifies ClientError is wrapped in SystemExit with secret id prefix."""
        secret_id = "kova-github-pat"
        field_name = "GITHUB_PAT_TOKEN"
        client = FakeSecretsManagerClient(error=_client_error(secret_id))

        with pytest.raises(SystemExit) as exc_info:
            load_secret_field(secret_id, field_name, client)

        message = str(exc_info.value)
        assert message.startswith(f"Could not load {secret_id} from Secrets Manager:")


class TestSecretsManagerClientProtocol:
    """Tests that fakes satisfy SecretsManagerClient for typing."""

    def test_fake_implements_protocol(self) -> None:
        """Verifies FakeSecretsManagerClient matches the Protocol surface."""
        client: SecretsManagerClient = FakeSecretsManagerClient(secret_string="{}")
        response = client.get_secret_value(SecretId="example")
        assert response == {"SecretString": "{}"}
