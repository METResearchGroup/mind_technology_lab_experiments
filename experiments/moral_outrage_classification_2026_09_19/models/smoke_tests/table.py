"""Build the smoke cost and latency table from PredictionRecords."""

from collections import defaultdict

import numpy as np

from shared.pricing import format_estimated_cost, smoke_model_order
from shared.records import PredictionRecord

SMOKE_STOP_MESSAGE = "SMOKE COMPLETE. Waiting for approval before the 1000-row jobs."


def build_smoke_table(records: list[PredictionRecord]) -> list[dict[str, object]]:
    """Group smoke records by model and return rows in the locked order.

    Parameters
    ----------
    records
        One record per text per model.

    Returns
    -------
    list[dict[str, object]]
        Rows with model_name, total_tokens, estimated_cost, estimated_runtime_ms.
    """
    grouped: dict[str, list[PredictionRecord]] = defaultdict(list)
    for record in records:
        grouped[record.model_name].append(record)
    rows: list[dict[str, object]] = []
    for model_name in smoke_model_order():
        model_records = grouped[model_name]
        rows.append(_row_from_records(model_name, model_records))
    return rows


def _row_from_records(
    model_name: str, model_records: list[PredictionRecord]
) -> dict[str, object]:
    input_tokens = _sum_tokens(model_records, "input_tokens")
    output_tokens = _sum_tokens(model_records, "output_tokens")
    total_tokens = input_tokens + output_tokens
    latencies = [record.latency_ms for record in model_records]
    median_runtime = float(np.median(latencies)) if latencies else 0.0
    return {
        "model_name": model_name,
        "total_tokens": total_tokens,
        "estimated_cost": format_estimated_cost(
            model_name, input_tokens, output_tokens
        ),
        "estimated_runtime_ms": median_runtime,
    }


def _sum_tokens(records: list[PredictionRecord], field_name: str) -> int:
    total = 0
    for record in records:
        value = getattr(record, field_name)
        if value is not None:
            total += int(value)
    return total


def render_smoke_markdown(rows: list[dict[str, object]]) -> str:
    """Render the smoke table as markdown."""
    lines = [
        "| model name | total tokens | estimated cost | estimated runtime |",
        "| --- | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| {row['model_name']} | {row['total_tokens']} | "
            f"{row['estimated_cost']} | {row['estimated_runtime_ms']:.1f} |"
        )
    return "\n".join(lines)
