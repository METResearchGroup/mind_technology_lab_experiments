"""Load allenai/xstest-response prompts with deduplication.

Run from the experiment folder:

    uv run python -c "from datasets import xstest; print(xstest.DATASET_NAME)"
"""

from __future__ import annotations

from shared.cache import iter_table_rows, load_hf_dataset
from shared.records import ExampleRecord
from shared.secrets import load_hf_token

DATASET_NAME = "xstest"
HF_REPO = "allenai/xstest-response"
PROMPT_HARMFUL = "prompt_harmful"
PROMPT_SAFE = "prompt_safe"


def load_records(split: str = "train") -> list[ExampleRecord]:
    """Load unique prompts from xstest-response (gated)."""
    token = load_hf_token()
    table = load_hf_dataset(HF_REPO, split=split, token=token)
    seen: set[str] = set()
    records: list[ExampleRecord] = []
    for index, row in enumerate(iter_table_rows(table)):
        prompt = str(row.get("prompt", row.get("text", ""))).strip()
        if not prompt or prompt in seen:
            continue
        seen.add(prompt)
        prompt_type = str(row.get("prompt_type", ""))
        is_harmful = prompt_type == PROMPT_HARMFUL
        is_safe = prompt_type == PROMPT_SAFE
        records.append(
            ExampleRecord(
                example_id=f"{DATASET_NAME}:{split}:{len(records)}",
                dataset=DATASET_NAME,
                split=split,
                text=prompt,
                gold_labels={"harmful": is_harmful},
                harm_category=None,
                is_benign_known=is_safe,
                metadata={"prompt_type": prompt_type},
            )
        )
    return records
