"""Write JSON artifacts for the dashboard: ``python -m user_role_vector``."""

from __future__ import annotations

import json
from pathlib import Path

from user_role_vector.paper_tables import PAPER
from user_role_vector.synthetic import run_mini_replication, write_results

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    results = run_mini_replication(seed=0)
    data_dir = ROOT / "data"
    write_results(data_dir / "mini_replication.json", results)
    write_results(data_dir / "paper_results.json", PAPER)
    dashboard_data = ROOT / "dashboard" / "public" / "data"
    write_results(dashboard_data / "mini_replication.json", results)
    write_results(dashboard_data / "paper_results.json", PAPER)
    print(json.dumps({"recovery_cosine": results["recovery_cosine"]}, indent=2))


if __name__ == "__main__":
    main()
