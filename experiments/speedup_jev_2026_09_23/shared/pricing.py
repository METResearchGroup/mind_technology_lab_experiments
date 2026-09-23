"""TypeSafe Jev price and cost estimate.

Run from the experiment folder:

    uv run python -c "from shared.pricing import estimate_jev_cost_usd; print(estimate_jev_cost_usd(349632, 0))"
"""

JEV_USD_PER_MILLION_INPUT_TOKENS = 0.042
JEV_USD_PER_MILLION_OUTPUT_TOKENS = 0.0
TOKENS_PER_MILLION = 1_000_000
PRICE_PAGE_URL = "https://docs.typesafe.ai/models"
PRICE_PAGE_DATE = "2026-09-23"


def estimate_jev_cost_usd(input_tokens: int, output_tokens: int) -> float:
    """Return the estimated USD cost of Jev tokens."""
    raise NotImplementedError
