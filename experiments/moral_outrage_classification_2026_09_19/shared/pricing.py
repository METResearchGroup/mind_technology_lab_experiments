"""Token cost lookup used by prediction records.

Run from the experiment folder:

    uv run python -c "from shared.pricing import estimate_cost_usd; print(estimate_cost_usd('Jev', 0, 0))"
"""

from shared.records import MODEL_NAME_PERSPECTIVE


def estimate_cost_usd(
    model_name: str, input_tokens: int | None, output_tokens: int | None
) -> float:
    """Return estimated USD cost. Perspective is 0. Other prices land in Step 5."""
    if model_name == MODEL_NAME_PERSPECTIVE:
        return 0.0
    return 0.0
