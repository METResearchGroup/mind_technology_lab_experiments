"""Hardcoded token prices copied from the public AWS Bedrock price page.

Run from the experiment folder:

    uv run python -c "from shared.pricing import estimate_cost_usd; print(estimate_cost_usd('Perspective API', None, None))"
"""

from shared.records import (
    BEDROCK_MODEL_NAMES,
    MODEL_NAME_JEV,
    MODEL_NAME_PERSPECTIVE,
)

TOKENS_PER_MILLION = 1_000_000
PRICE_PAGE_URL = "https://aws.amazon.com/bedrock/pricing/"
PRICE_PAGE_DATE = "2026-09-19"

# USD per 1M tokens (input, output) for us-east-2 on-demand / US inference profiles.
# Copied 2026-09-19 from PRICE_PAGE_URL and the us-east-2 listings for IDs
# that the static price tables do not expand.
BEDROCK_USD_PER_MILLION: dict[str, tuple[float, float]] = {
    "Bedrock:us.openai.gpt-5.6-luna": (0.22, 1.32),
    "Bedrock:us.openai.gpt-5.6-terra": (2.20, 13.20),
    "Bedrock:us.anthropic.claude-sonnet-5": (3.00, 15.00),
    "Bedrock:qwen.qwen3-32b-v1:0": (0.15, 0.60),
    "Bedrock:deepseek.v3-v1:0": (0.58, 1.68),
}


def estimate_cost_usd(
    model_name: str, input_tokens: int | None, output_tokens: int | None
) -> float:
    """Return estimated USD cost. Perspective is 0. Jev has no public price."""
    if model_name == MODEL_NAME_PERSPECTIVE:
        return 0.0
    if model_name == MODEL_NAME_JEV:
        return 0.0
    if model_name not in BEDROCK_USD_PER_MILLION:
        raise ValueError(f"No price table row for {model_name}")
    input_price, output_price = BEDROCK_USD_PER_MILLION[model_name]
    input_count = 0 if input_tokens is None else input_tokens
    output_count = 0 if output_tokens is None else output_tokens
    return (
        input_count * input_price + output_count * output_price
    ) / TOKENS_PER_MILLION


def format_estimated_cost(
    model_name: str, input_tokens: int | None, output_tokens: int | None
) -> str:
    """Format cost to 6 decimals, or unknown for Jev."""
    if model_name == MODEL_NAME_JEV:
        return "unknown"
    return f"{estimate_cost_usd(model_name, input_tokens, output_tokens):.6f}"


def smoke_model_order() -> tuple[str, ...]:
    """Return the seven smoke-table model names in issue-17 order."""
    return (MODEL_NAME_JEV, MODEL_NAME_PERSPECTIVE, *BEDROCK_MODEL_NAMES)
