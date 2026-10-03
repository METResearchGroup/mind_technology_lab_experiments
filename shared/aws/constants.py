# ruff: noqa: E501
"""Shared AWS constants for repository helpers.

Run from the repository root:

    uv run python -c "from shared.aws.constants import DEFAULT_REGION_NAME; print(DEFAULT_REGION_NAME)"
"""

DEFAULT_REGION_NAME = "us-east-2"

# Lab S3 bucket for experiment artifacts. Prefixes match the local folder path.
DEFAULT_BUCKET = "mind-technology-lab-experiments"
