"""Load ToxicChat toxicchat0124 rows as ExampleRecord.

Run from the experiment folder:

    uv run python -c "from datasets import toxicchat; print(toxicchat.DATASET_NAME)"
"""

from __future__ import annotations

from shared.cache import iter_table_rows, load_hf_dataset
from shared.records import ExampleRecord

DATASET_NAME = "toxicchat"
HF_REPO = "lmsys/toxic-chat"
HF_CONFIG = "toxicchat0124"


def load_records(split: str = "test") -> list[ExampleRecord]:
    """Load ToxicChat rows for the given split."""
    table = load_hf_dataset(HF_REPO, name=HF_CONFIG, split=split)
    records: list[ExampleRecord] = []
    for index, row in enumerate(iter_table_rows(table)):
        records.append(
            ExampleRecord(
                example_id=f"{DATASET_NAME}:{split}:{index}",
                dataset=DATASET_NAME,
                split=split,
                text=str(row["user_input"]).strip(),
                gold_labels={
                    "toxic": int(row["toxicity"]) == 1,
                    "jailbreak": int(row["jailbreaking"]) == 1,
                },
                harm_category=None,
                is_benign_known=False,
                metadata={},
            )
        )
    return records
