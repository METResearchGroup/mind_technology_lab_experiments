from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(
    "autoresearch/verbalized_eval_awareness_inflates_measured_safety_2026_09_12"
)
CLAIMS = ROOT / "dashboard" / "claims.json"
SPECS = ROOT / "experiments" / "specs.json"
DASHBOARD = ROOT / "dashboard" / "index.html"


def test_claims_json_has_five_findings() -> None:
    claims = json.loads(CLAIMS.read_text())
    ids = [item["id"] for item in claims["findings"]]
    assert ids == ["f1", "f2", "f3", "f4", "f5"]
    assert "overstate" in claims["headline"].lower()


def test_five_experiments_stay_under_two_dollars() -> None:
    specs = json.loads(SPECS.read_text())
    experiments = specs["experiments"]
    assert len(experiments) == 5
    assert specs["default_model"] == "Qwen/Qwen3.5-4B"
    assert specs["budget_usd_per_experiment"] == 2.0
    for experiment in experiments:
        assert experiment["estimated_usd"] <= specs["budget_usd_per_experiment"]
        assert experiment["n_generations"] > 0
        assert experiment["id"].startswith("e")


def test_dashboard_covers_findings_and_experiments() -> None:
    html = DASHBOARD.read_text()
    for needle in (
        "Verbalized eval awareness inflates measured safety",
        "Finding 1",
        "Finding 5",
        'id="e1"',
        'id="e5"',
        "Qwen/Qwen3.5-4B",
        "Skip to content",
        "pick",
    ):
        assert needle in html
