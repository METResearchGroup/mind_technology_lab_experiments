"""Load HarmBench DirectRequest and HumanJailbreaks test rows.

Run from the experiment folder:

    uv run python -c "from datasets import harmbench; print(harmbench.DATASET_NAME)"
"""

from __future__ import annotations

from shared.cache import iter_table_rows, load_hf_dataset
from shared.records import ExampleRecord

DATASET_NAME = "harmbench"
HF_REPO = "swiss-ai/harmbench"
CONFIGS = ("DirectRequest", "HumanJailbreaks")


def load_records(split: str = "test") -> list[ExampleRecord]:
    """Load both HarmBench configs for the test split."""
    records: list[ExampleRecord] = []
    for config in CONFIGS:
        table = load_hf_dataset(HF_REPO, name=config, split=split)
        for index, row in enumerate(iter_table_rows(table)):
            behavior = str(row.get("Behavior", row.get("behavior", ""))).strip()
            text = str(row.get("prompt", row.get("text", behavior))).strip()
            records.append(
                ExampleRecord(
                    example_id=f"{DATASET_NAME}:{config}:{split}:{index}",
                    dataset=DATASET_NAME,
                    split=split,
                    text=text or behavior,
                    gold_labels={"harm": True},
                    harm_category=str(row.get("Category", row.get("category", "")))
                    or None,
                    is_benign_known=False,
                    metadata={"config": config},
                )
            )
    return records
