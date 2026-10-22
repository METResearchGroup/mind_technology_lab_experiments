"""Load dair-ai/emotion split rows as ExampleRecord.

Run from the experiment folder:

    uv run python -c "from datasets import emotion; print(emotion.DATASET_NAME)"
"""

from __future__ import annotations

from shared.cache import iter_table_rows, load_hf_dataset
from shared.records import ExampleRecord

DATASET_NAME = "emotion"
HF_REPO = "dair-ai/emotion"
HF_CONFIG = "split"
LABELS = ("sadness", "joy", "love", "anger", "fear", "surprise")


def load_records(split: str = "test") -> list[ExampleRecord]:
    """Load Emotion classification rows."""
    table = load_hf_dataset(HF_REPO, name=HF_CONFIG, split=split)
    records: list[ExampleRecord] = []
    for index, row in enumerate(iter_table_rows(table)):
        label_index = int(row["label"])
        label_name = LABELS[label_index] if label_index < len(LABELS) else str(
            label_index
        )
        records.append(
            ExampleRecord(
                example_id=f"{DATASET_NAME}:{split}:{index}",
                dataset=DATASET_NAME,
                split=split,
                text=str(row["text"]).strip(),
                gold_labels=label_name,
                harm_category=None,
                is_benign_known=False,
                metadata={},
            )
        )
    return records
