"""Load Do-Not-Answer rows; question text stays in gitignored snapshots only.

Run from the experiment folder:

    uv run python -c "from datasets import do_not_answer; print(do_not_answer.DATASET_NAME)"
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from shared.cache import iter_table_rows, load_hf_dataset
from shared.records import ExampleRecord
from shared.secrets import load_hf_token

DATASET_NAME = "do_not_answer"
HF_REPO = "LibrAI/do-not-answer"
SNAPSHOT_DIR = Path(__file__).resolve().parent.parent / "data" / "snapshots" / DATASET_NAME


def load_records(split: str = "train") -> list[ExampleRecord]:
    """Load Do-Not-Answer rows without writing question text to committed paths."""
    token = load_hf_token()
    table = load_hf_dataset(HF_REPO, split=split, token=token)
    _write_snapshot(table, split)
    records: list[ExampleRecord] = []
    for index, row in enumerate(iter_table_rows(table)):
        risk_area = str(row.get("risk_area", ""))
        harm_type = str(row.get("types_of_harm", row.get("type_of_harm", "")))
        text = str(row.get("question", row.get("text", ""))).strip()
        records.append(
            ExampleRecord(
                example_id=f"{DATASET_NAME}:{split}:{index}",
                dataset=DATASET_NAME,
                split=split,
                text=text,
                gold_labels={"refuse": True},
                harm_category=risk_area or None,
                is_benign_known=False,
                metadata={
                    "risk_area": risk_area,
                    "type_of_harm": harm_type,
                },
            )
        )
    return records


def _write_snapshot(table: object, split: str) -> None:
    """Persist raw rows under data/snapshots (gitignored)."""
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    path = SNAPSHOT_DIR / f"{split}.parquet"
    frame = table.to_pandas() if hasattr(table, "to_pandas") else pd.DataFrame(table)
    frame.to_parquet(path, index=False)
