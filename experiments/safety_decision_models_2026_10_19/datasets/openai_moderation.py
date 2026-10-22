"""Load OpenAI moderation evaluation rows as ExampleRecord.

Run from the experiment folder:

    uv run python -c "from datasets import openai_moderation; print(openai_moderation.DATASET_NAME)"
"""

from __future__ import annotations

from shared.cache import iter_table_rows, load_hf_dataset
from shared.records import ExampleRecord

DATASET_NAME = "openai_moderation"
HF_REPO = "mmathys/openai-moderation-api-evaluation"
CATEGORY_CODES = ("S", "H", "V", "HR", "SH", "S3", "H2", "V2")


def _category_positive(row: dict[str, object], code: str) -> bool:
    value = row.get(code)
    if value is None:
        return False
    return int(value) == 1


def load_records(split: str = "train") -> list[ExampleRecord]:
    """Load moderation rows (single train split on the hub)."""
    table = load_hf_dataset(HF_REPO, split=split)
    records: list[ExampleRecord] = []
    for index, row in enumerate(iter_table_rows(table)):
        gold = {code: _category_positive(row, code) for code in CATEGORY_CODES}
        records.append(
            ExampleRecord(
                example_id=f"{DATASET_NAME}:{split}:{index}",
                dataset=DATASET_NAME,
                split=split,
                text=str(row["prompt"]).strip(),
                gold_labels=gold,
                harm_category=None,
                is_benign_known=False,
                metadata={},
            )
        )
    return records
