"""Score the 1,000-row sample with Jev.

Run from the experiment folder after smoke approval:

    uv run python scripts/run_jev.py
"""

import argparse
from pathlib import Path

import pandas as pd

from models.jev import JevEngine
from shared.data import DATA_DIR, SAMPLE_MANIFEST_NAME, SAMPLE_PARQUET_NAME
from shared.run_outputs import (
    assert_run_complete,
    load_deadletters,
    load_records_from_output,
    require_sample_manifest,
    tasks_from_sample,
    write_model_outputs,
)

EXPERIMENT_ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    args = _parse_args()
    run_jev(Path(args.sample_path), Path(args.manifest_path), Path(args.output_dir))


def run_jev(sample_path: Path, manifest_path: Path, output_dir: Path) -> None:
    """Load the sample, score with Jev, and write model outputs."""
    require_sample_manifest(manifest_path)
    frame = pd.read_parquet(sample_path)
    engine = JevEngine()
    engine.label_records(tasks_from_sample(frame), output_dir)
    records = load_records_from_output(output_dir)
    deadletters = load_deadletters(output_dir)
    assert_run_complete(len(records), len(deadletters), len(frame))
    write_model_outputs(records, deadletters, output_dir)
    print(f"DONE Jev scored={len(records)} deadletter={len(deadletters)}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-path", default=str(DATA_DIR / SAMPLE_PARQUET_NAME))
    parser.add_argument(
        "--manifest-path", default=str(DATA_DIR / SAMPLE_MANIFEST_NAME)
    )
    parser.add_argument(
        "--output-dir", default=str(EXPERIMENT_ROOT / "outputs" / "jev")
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()
