"""Score the 1,000-row sample with all five Bedrock models.

Run from the experiment folder after smoke approval:

    uv run python scripts/run_bedrock.py
"""

import argparse
import sys
from pathlib import Path

EXPERIMENT_ROOT = Path(__file__).resolve().parent.parent
if str(EXPERIMENT_ROOT) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_ROOT))

import pandas as pd

from models.bedrock import BedrockEngine
from shared.data import DATA_DIR, SAMPLE_MANIFEST_NAME, SAMPLE_PARQUET_NAME
from shared.records import BEDROCK_MODEL_IDS
from shared.run_outputs import (
    assert_run_complete,
    load_deadletters,
    load_records_from_output,
    outstanding_deadletters,
    require_sample_manifest,
    tasks_from_sample,
    write_model_outputs,
)

def main() -> None:
    args = _parse_args()
    run_bedrock(
        Path(args.sample_path),
        Path(args.manifest_path),
        Path(args.output_root),
    )


def run_bedrock(
    sample_path: Path, manifest_path: Path, output_root: Path
) -> None:
    """Score each locked Bedrock model id in sequence."""
    require_sample_manifest(manifest_path)
    frame = pd.read_parquet(sample_path)
    tasks = tasks_from_sample(frame)
    for model_id in BEDROCK_MODEL_IDS:
        output_dir = output_root / "bedrock" / model_id
        engine = BedrockEngine(model_id)
        engine.label_records(tasks, output_dir)
        records = load_records_from_output(output_dir)
        deadletters = outstanding_deadletters(records, load_deadletters(output_dir))
        assert_run_complete(len(records), len(deadletters), len(tasks))
        write_model_outputs(records, deadletters, output_dir)
        print(
            f"DONE Bedrock:{model_id} scored={len(records)} "
            f"deadletter={len(deadletters)}"
        )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-path", default=str(DATA_DIR / SAMPLE_PARQUET_NAME))
    parser.add_argument(
        "--manifest-path", default=str(DATA_DIR / SAMPLE_MANIFEST_NAME)
    )
    parser.add_argument("--output-root", default=str(EXPERIMENT_ROOT / "outputs"))
    return parser.parse_args()


if __name__ == "__main__":
    main()
