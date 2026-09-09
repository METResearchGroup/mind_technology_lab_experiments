from __future__ import annotations

from lifemem.config import LifeMemConfig
from lifemem.experiment import run_suite


def test_lifemem_beats_profile_on_kl() -> None:
    results = run_suite(
        LifeMemConfig(
            seed=42,
            methods=(
                "direct",
                "profile",
                "event_rag",
                "full_history",
                "lifemem",
                "lifemem_no_param",
                "lifemem_no_struct",
            ),
        ),
        n_agents=12,
        n_waves=4,
        events_per_wave=6,
    )
    kl = {method: results["methods"][method]["kl"] for method in results["methods"]}
    assert kl["lifemem"] < kl["profile"]
    assert kl["lifemem"] < kl["direct"]
    assert kl["lifemem"] < kl["event_rag"]
    assert kl["lifemem"] < kl["lifemem_no_param"]
    assert kl["lifemem"] <= kl["lifemem_no_struct"]
    assert (
        results["identity"]["profile"]["silhouette"]
        > results["identity"]["human"]["silhouette"]
    )
