"""Load ToxiGen annotated test rows as ExampleRecord.

Run from the experiment folder:

    uv run python -c "from datasets import toxigen; print(len(toxigen.load_records('test')[:1]))"
"""

from __future__ import annotations

from shared.cache import iter_table_rows, load_hf_dataset
from shared.records import ExampleRecord

DATASET_NAME = "toxigen"
HF_REPO = "toxigen/toxigen-data"
HF_CONFIG = "annotated"
TOXICITY_BIN_THRESHOLD = 5.5


def load_records(split: str = "test") -> list[ExampleRecord]:
    """Load ToxiGen rows for the given split."""
    table = load_hf_dataset(HF_REPO, name=HF_CONFIG, split=split)
    records: list[ExampleRecord] = []
    for index, row in enumerate(iter_table_rows(table)):
        toxic = row["toxicity_ai"] + row["toxicity_human"] > TOXICITY_BIN_THRESHOLD
        text = str(row["text"]).strip()
        records.append(
            ExampleRecord(
                example_id=f"{DATASET_NAME}:{split}:{index}",
                dataset=DATASET_NAME,
                split=split,
                text=text,
                gold_labels={
                    "toxic": toxic,
                    "toxicity": int(row["toxicity_human"]) - 1,
                },
                harm_category=None,
                is_benign_known=False,
                metadata={},
            )
        )
    return records
