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
        assert experiment["n_generations"] == experiment["n_judge_calls"]
        assert experiment["id"].startswith("e")

    by_id = {item["id"]: item for item in experiments}
    assert "One rollout per item" in by_id["e1"]["design"]
    assert by_id["e1"]["n_generations"] == 100
    assert by_id["e2"]["n_generations"] == 28 * 10
    assert by_id["e3"]["n_generations"] == 16 * 3 * 5
    assert by_id["e4"]["n_generations"] == 12 * 8 * 2
    assert by_id["e5"]["n_generations_4b_only"] == 30 * 2 * 3
    assert by_id["e5"]["n_generations"] == 30 * 2 * 2 * 3
    assert by_id["e5"]["n_judge_calls_4b_only"] == by_id["e5"]["n_generations_4b_only"]


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
        "100 gens + 100 judge calls",
        "0/100",
        "180 gens (4B) or 360 with 0.8B",
        "MAX_PICKS = 2",
        "Pick at most two",
    ):
        assert needle in html

    for n in range(1, 6):
        assert f'<h3 id="e{n}-heading">' in html
        assert f'name="pick" value="e{n}" aria-labelledby="e{n}-heading"' in html
