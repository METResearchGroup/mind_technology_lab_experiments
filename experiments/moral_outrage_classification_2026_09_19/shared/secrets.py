"""Load TypeSafe and Google API keys from Secrets Manager in us-east-2.

Run from the experiment folder:

    uv run python -m shared.secrets
"""


def load_secret_field(secret_id: str, field_name: str, client: object) -> str:
    """Read one JSON field from a Secrets Manager secret."""
    raise NotImplementedError


def load_typesafe_api_key() -> str:
    """Load TYPESAFE_API_KEY from secret jev-typesafe-api-key."""
    raise NotImplementedError


def load_google_api_key() -> str:
    """Load GOOGLE_API_KEY from secret google-api-key."""
    raise NotImplementedError


def load_api_keys() -> tuple[str, str]:
    """Load TypeSafe and Google keys. Never print the values."""
    raise NotImplementedError
