"""Load GoEmotions simplified split as ExampleRecord.

Run from the experiment folder:

    uv run python -c "from datasets import go_emotions; print(go_emotions.DATASET_NAME)"
"""

from __future__ import annotations

from shared.cache import iter_table_rows, load_hf_dataset
from shared.records import ExampleRecord

DATASET_NAME = "go_emotions"
HF_REPO = "google-research-datasets/go_emotions"
HF_CONFIG = "simplified"


def _label_names(table: object) -> list[str]:
    features = getattr(table, "features", None)
    if features and "labels" in features:
        names = features["labels"].feature.names
        if names:
            return list(names)
    return []


def load_records(split: str = "test") -> list[ExampleRecord]:
    """Load GoEmotions rows with multi-label gold map."""
    table = load_hf_dataset(HF_REPO, name=HF_CONFIG, split=split)
    label_names = _label_names(table)
    records: list[ExampleRecord] = []
    for index, row in enumerate(iter_table_rows(table)):
        active = row.get("labels", [])
        if label_names:
            gold = {
                name: int(idx) in active for idx, name in enumerate(label_names)
            }
        else:
            gold = {str(label): True for label in active}
        records.append(
            ExampleRecord(
                example_id=f"{DATASET_NAME}:{split}:{index}",
                dataset=DATASET_NAME,
                split=split,
                text=str(row["text"]).strip(),
                gold_labels=gold,
                harm_category=None,
                is_benign_known=False,
                metadata={},
            )
        )
    return records
