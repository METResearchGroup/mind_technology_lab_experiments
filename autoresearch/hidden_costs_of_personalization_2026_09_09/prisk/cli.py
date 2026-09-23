"""CLI for the PRISK mini-replication."""

from __future__ import annotations

import argparse
from pathlib import Path

from prisk.evaluate import run_replication

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the PRISK mini-replication.")
    parser.add_argument("--backend", choices=("mock", "hf"), default="mock")
    parser.add_argument(
        "--hf-model",
        default="Qwen/Qwen3.5-4B:featherless-ai",
        help="Hugging Face router model id, including provider suffix.",
    )
    parser.add_argument(
        "--hf-local",
        action="store_true",
        help="Skip the Inference Router and run Qwen from a Hub GGUF locally.",
    )
    parser.add_argument(
        "--allow-mock-fallback",
        action="store_true",
        help="If Hugging Face Qwen serving fails, fall back to the mock policy.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=ROOT / "results",
    )
    args = parser.parse_args()
    summary = run_replication(
        backend=args.backend,
        hf_model=args.hf_model,
        out_dir=args.out_dir,
        prefer_local=args.hf_local,
        allow_mock_fallback=args.allow_mock_fallback,
    )
    print(f"backend={summary['backend']} model={summary['model_name']}")
    print(f"wrote {args.out_dir / 'replication_summary.json'}")
    print(f"wrote {ROOT / 'dashboard' / 'data' / 'replication.json'}")
    for line in summary["takeaways"]:
        print(f"- {line}")
    for row in summary["aggregate"]["rows"]:
        print(
            f"{row['risk_type']:<28} {row['setting']:<18} "
            f"irp={row['irp_resistance_pct']} uir={row['uir_pct']} "
            f"syco={row['syco_resistance_pct']}"
        )


if __name__ == "__main__":
    main()
