"""Load WildGuardMix WildGuardTest rows as ExampleRecord.

Run from the experiment folder:

    uv run python -c "from datasets import wildguardmix; print(wildguardmix.DATASET_NAME)"
"""

from __future__ import annotations

from shared.cache import iter_table_rows, load_hf_dataset
from shared.records import ExampleRecord
from shared.secrets import load_hf_token

DATASET_NAME = "wildguardmix"
HF_REPO = "allenai/wildguardmix"
HF_CONFIG = "wildguardtest"
HUB_SPLIT = "test"
SPLIT_NAME = "WildGuardTest"


def load_records(split: str = SPLIT_NAME) -> list[ExampleRecord]:
    """Load WildGuardTest rows (gated; requires hf-token)."""
    token = load_hf_token()
    table = load_hf_dataset(
        HF_REPO, name=HF_CONFIG, split=HUB_SPLIT, token=token
    )
    records: list[ExampleRecord] = []
    for index, row in enumerate(iter_table_rows(table)):
        prompt_harm = bool(row.get("prompt_harm_label"))
        adversarial = bool(row.get("adversarial"))
        benign_prompt = not prompt_harm
        records.append(
            ExampleRecord(
                example_id=f"{DATASET_NAME}:{SPLIT_NAME}:{index}",
                dataset=DATASET_NAME,
                split=SPLIT_NAME,
                text=str(row["prompt"]).strip(),
                gold_labels={
                    "prompt_harm": prompt_harm,
                    "adversarial": adversarial,
                },
                harm_category=None,
                is_benign_known=benign_prompt,
                metadata={"adversarial": adversarial},
            )
        )
    return records
