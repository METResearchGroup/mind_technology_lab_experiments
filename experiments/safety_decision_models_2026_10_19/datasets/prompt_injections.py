"""Load deepset prompt-injections rows as ExampleRecord.

Run from the experiment folder:

    uv run python -c "from datasets import prompt_injections; print(prompt_injections.DATASET_NAME)"
"""

from __future__ import annotations

from shared.cache import iter_table_rows, load_hf_dataset
from shared.records import ExampleRecord

DATASET_NAME = "prompt_injections"
HF_REPO = "deepset/prompt-injections"


def load_records(split: str = "test") -> list[ExampleRecord]:
    """Load prompt injection rows for the given split."""
    table = load_hf_dataset(HF_REPO, split=split)
    records: list[ExampleRecord] = []
    for index, row in enumerate(iter_table_rows(table)):
        records.append(
            ExampleRecord(
                example_id=f"{DATASET_NAME}:{split}:{index}",
                dataset=DATASET_NAME,
                split=split,
                text=str(row["text"]).strip(),
                gold_labels={"answer": int(row["label"]) == 1},
                harm_category=None,
                is_benign_known=False,
                metadata={},
            )
        )
    return records
