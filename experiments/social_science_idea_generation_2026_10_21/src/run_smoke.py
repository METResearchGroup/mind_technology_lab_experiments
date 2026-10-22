# ruff: noqa: E501
"""Smoke entrypoint: one round, cost estimate, local JSON, and S3 upload.

Run from the repository root:

    PYTHONPATH=/workspace:/workspace/experiments/social_science_idea_generation_2026_10_21 \\
      uv run --project experiments/social_science_idea_generation_2026_10_21 \\
      python -m src.run_smoke
"""

from __future__ import annotations

import sys
from pathlib import Path

from langsmith import uuid7
from workflow.constants import EXPERIMENT_NAME, S3_BUCKET
from workflow.cost import CostEstimate, estimate_full_run_cost

from shared.aws.constants import DEFAULT_REGION_NAME
from shared.aws.s3 import S3
from src.run_round import run_round

_OUTPUTS_DIR = "outputs"
_SMOKE_DIR = "smoke"
_INPUTS_DIR = "inputs"
_BRIEF_FILENAME = "brief.md"
_ROUND_JSON = "round.json"
_COST_JSON = "cost.json"
_S3_EXPERIMENTS_PREFIX = "experiments"


def _experiment_root() -> Path:
    """Return the experiment directory that contains ``src/`` and ``inputs/``."""
    return Path(__file__).resolve().parents[1]


def _read_brief(brief_path: Path) -> str:
    """Read the brief file as UTF-8 without stripping."""
    return brief_path.read_text(encoding="utf-8")


def _smoke_output_dir(experiment_root: Path, run_id: str) -> Path:
    """Return ``outputs/smoke/<run_id>/`` under the experiment root."""
    return experiment_root / _OUTPUTS_DIR / _SMOKE_DIR / run_id


def _write_smoke_json(
    output_dir: Path,
    round_record_json: str,
    cost_json: str,
) -> tuple[Path, Path]:
    """Write ``round.json`` and ``cost.json``; return their paths."""
    output_dir.mkdir(parents=True, exist_ok=True)
    round_path = output_dir / _ROUND_JSON
    cost_path = output_dir / _COST_JSON
    round_path.write_text(round_record_json, encoding="utf-8")
    cost_path.write_text(cost_json, encoding="utf-8")
    return round_path, cost_path


def _s3_object_key(run_id: str, filename: str) -> str:
    """Build the S3 key for one smoke artifact."""
    return (
        f"{_S3_EXPERIMENTS_PREFIX}/{EXPERIMENT_NAME}/{_SMOKE_DIR}/{run_id}/{filename}"
    )


def _upload_smoke_files(round_path: Path, cost_path: Path, run_id: str) -> None:
    """Upload local smoke JSON files to the experiment prefix in S3."""
    s3 = S3(S3_BUCKET, region_name=DEFAULT_REGION_NAME)
    s3.upload_file(round_path, _s3_object_key(run_id, _ROUND_JSON))
    s3.upload_file(cost_path, _s3_object_key(run_id, _COST_JSON))


def run_smoke(brief_path: Path, run_id: str) -> CostEstimate:
    """Run round 1, estimate full-study cost, persist artifacts, and upload to S3.

    Parameters
    ----------
    brief_path
        UTF-8 brief file; contents are passed to ``run_round`` unchanged.
    run_id
        Identifier for this smoke run (output and S3 paths).

    Returns
    -------
    CostEstimate
        Projected token totals and USD for a full five-round study plus vote.
    """
    brief = _read_brief(brief_path)
    round_record = run_round(1, brief, run_id)
    estimate = estimate_full_run_cost(round_record)
    output_dir = _smoke_output_dir(_experiment_root(), run_id)
    round_path, cost_path = _write_smoke_json(
        output_dir,
        round_record.model_dump_json(indent=2),
        estimate.model_dump_json(indent=2),
    )
    _upload_smoke_files(round_path, cost_path, run_id)
    return estimate


def _default_brief_path() -> Path:
    """Return the default ``inputs/brief.md`` path."""
    return _experiment_root() / _INPUTS_DIR / _BRIEF_FILENAME


def _resolve_run_id(argv: list[str]) -> str:
    """Parse ``run_id`` from argv or generate one with ``uuid7``."""
    if len(argv) == 2:
        return argv[1]
    return str(uuid7())


def main() -> None:
    """CLI entry: run smoke and print ``run_id`` and ``estimated_cost_usd``."""
    run_id = _resolve_run_id(sys.argv)
    estimate = run_smoke(_default_brief_path(), run_id)
    print(f"run_id {run_id}")
    print(f"estimated_cost_usd {estimate.estimated_cost_usd}")


if __name__ == "__main__":
    main()
