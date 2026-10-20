"""Load JailbreakBench harmful and benign behavior splits.

Run from the experiment folder:

    uv run python -c "from datasets import jailbreakbench; print(jailbreakbench.DATASET_NAME)"
"""

from __future__ import annotations

from shared.cache import iter_table_rows, load_hf_dataset
from shared.records import ExampleRecord

DATASET_NAME = "jailbreakbench"
HF_REPO = "JailbreakBench/JBB-Behaviors"
HF_CONFIG = "behaviors"
SPLITS = ("harmful", "benign")


def load_records(split: str | None = None) -> list[ExampleRecord]:
    """Load harmful and benign splits unless one split is requested."""
    target_splits = (split,) if split else SPLITS
    records: list[ExampleRecord] = []
    for split_name in target_splits:
        table = load_hf_dataset(HF_REPO, name=HF_CONFIG, split=split_name)
        benign = split_name == "benign"
        for index, row in enumerate(iter_table_rows(table)):
            goal = str(row.get("Goal", row.get("goal", row.get("text", "")))).strip()
            records.append(
                ExampleRecord(
                    example_id=f"{DATASET_NAME}:{split_name}:{index}",
                    dataset=DATASET_NAME,
                    split=split_name,
                    text=goal,
                    gold_labels={"harmful": not benign},
                    harm_category=None,
                    is_benign_known=benign,
                    metadata={"behavior": str(row.get("Behavior", ""))},
                )
            )
    return records
