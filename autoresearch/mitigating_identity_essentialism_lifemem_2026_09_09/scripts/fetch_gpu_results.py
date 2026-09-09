#!/usr/bin/env python3
"""Pull gpu_results.json from the Hub dataset after a Jobs run finishes."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from huggingface_hub import hf_hub_download
from lifemem.artifacts import DEFAULT_RESULTS_REPO


def main() -> None:
    repo = os.environ.get("LIFEMEM_RESULTS_REPO", DEFAULT_RESULTS_REPO)
    path = hf_hub_download(
        repo_id=repo,
        repo_type="dataset",
        filename="gpu_results.json",
        token=os.environ.get("HF_TOKEN"),
    )
    dest = ROOT / "data" / "gpu_results.json"
    dest.write_bytes(Path(path).read_bytes())
    data = json.loads(dest.read_text(encoding="utf-8"))
    print(
        json.dumps(
            {"path": str(dest), "kl": {k: v["kl"] for k, v in data["methods"].items()}},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
