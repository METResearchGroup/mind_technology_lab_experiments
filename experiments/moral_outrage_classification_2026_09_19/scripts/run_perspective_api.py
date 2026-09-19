"""Score the 1,000-row sample with Perspective.

Run from the experiment folder after smoke approval:

    uv run python scripts/run_perspective_api.py
"""

import argparse
from pathlib import Path

import pandas as pd

from models.perspective_api import PerspectiveApiEngine
from shared.data import (
    DATA_DIR,
    SAMPLE_MANIFEST_NAME,
    SAMPLE_PARQUET_NAME,
    download_perspective_labels_csv,
    load_perspective_labels_frame,
    missing_perspective_source_row_ids,
)
from shared.run_outputs import (
    assert_run_complete,
    load_deadletters,
    load_records_from_output,
    outstanding_deadletters,
    require_sample_manifest,
    tasks_from_sample,
    write_model_outputs,
)

EXPERIMENT_ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    args = _parse_args()
    run_perspective(
        Path(args.sample_path), Path(args.manifest_path), Path(args.output_dir)
    )


def run_perspective(
    sample_path: Path, manifest_path: Path, output_dir: Path
) -> None:
    """Load the sample, score with Perspective, and write model outputs."""
    require_sample_manifest(manifest_path)
    frame = pd.read_parquet(sample_path)
    labels = load_perspective_labels_frame(download_perspective_labels_csv())
    missing_ids = missing_perspective_source_row_ids(frame, labels)
    missing_set = set(missing_ids)
    scored_frame = frame.loc[
        ~frame["source_row_id"].astype(str).isin(missing_set)
    ].copy()
    engine = PerspectiveApiEngine()
    engine.label_records(tasks_from_sample(scored_frame), output_dir)
    records = load_records_from_output(output_dir)
    deadletters = outstanding_deadletters(records, load_deadletters(output_dir))
    assert_run_complete(len(records), len(deadletters), len(frame) - len(missing_ids))
    write_model_outputs(
        records, deadletters, output_dir, n_missing_label=len(missing_ids)
    )
    print(
        f"DONE Perspective API scored={len(records)} "
        f"missing_label={len(missing_ids)} deadletter={len(deadletters)}"
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-path", default=str(DATA_DIR / SAMPLE_PARQUET_NAME))
    parser.add_argument(
        "--manifest-path", default=str(DATA_DIR / SAMPLE_MANIFEST_NAME)
    )
    parser.add_argument(
        "--output-dir",
        default=str(EXPERIMENT_ROOT / "outputs" / "perspective_api"),
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()
