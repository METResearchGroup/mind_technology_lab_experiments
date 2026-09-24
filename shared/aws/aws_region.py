"""Hardcoded AWS region for shared Secrets Manager access.

Run from the repository root:

    uv run python -c "from shared.aws.aws_region import AWS_REGION; print(AWS_REGION)"
"""

AWS_REGION = "us-east-2"
