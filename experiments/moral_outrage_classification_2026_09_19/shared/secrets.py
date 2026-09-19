"""Load TypeSafe and Google API keys from Secrets Manager in us-east-2.

Run from the experiment folder:

    uv run python -m shared.secrets
"""

TYPESAFE_SECRET_ID = "jev-typesafe-api-key"
TYPESAFE_FIELD_NAME = "TYPESAFE_API_KEY"
GOOGLE_SECRET_ID = "google-api-key"
GOOGLE_FIELD_NAME = "GOOGLE_API_KEY"
LAB_ACCESS_KEY_ID_ENV = "LAB_AWS_ACCESS_KEY_ID"
LAB_SECRET_ACCESS_KEY_ENV = "LAB_AWS_ACCESS_KEY_SECRET"
ACCESS_KEY_ID_ENV = "AWS_ACCESS_KEY_ID"
SECRET_ACCESS_KEY_ENV = "AWS_SECRET_ACCESS_KEY"
ACCESS_KEY_SECRET_ENV = "AWS_ACCESS_KEY_SECRET"


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
