# ruff: noqa: E501
"""Load HarmBench, AdvBench, and AgentHarm into one example shape.

Run from the repository root:

    uv run --project experiments/safety_prompting_2026_10_16 python -c "from experiments.safety_prompting_2026_10_16.dataloader import load_examples; print(len(load_examples('advbench')))"
"""

from __future__ import annotations

from dataclasses import dataclass

from datasets import load_dataset

DATASET_NAMES = ("harmbench", "advbench", "agentharm")


@dataclass(frozen=True)
class Example:
    """One prompt to send to the model."""

    example_id: str
    prompt: str
    metadata: dict[str, str]


@dataclass(frozen=True)
class DatasetSpec:
    """Hugging Face coordinates for one command-line dataset name."""

    name: str
    repo: str
    config: str | None
    split: str


SPECS: dict[str, DatasetSpec] = {
    "harmbench": DatasetSpec(
        name="harmbench",
        repo="swiss-ai/harmbench",
        config="DirectRequest",
        split="test",
    ),
    "advbench": DatasetSpec(
        name="advbench",
        repo="walledai/AdvBench",
        config=None,
        split="train",
    ),
    "agentharm": DatasetSpec(
        name="agentharm",
        repo="ai-safety-institute/AgentHarm",
        config="harmful",
        split="test_public",
    ),
}


def harmbench_prompt(behavior: str, context: str | None) -> str:
    """Join a HarmBench behavior with its context string when the context is present."""
    behavior_text = behavior.strip()
    context_text = (context or "").strip()
    if context_text:
        return f"{context_text}\n\n{behavior_text}"
    return behavior_text


def load_examples(dataset_name: str) -> list[Example]:
    """Load one dataset in a stable order.

    Parameters
    ----------
    dataset_name
        ``harmbench``, ``advbench``, or ``agentharm``.

    Returns
    -------
    list[Example]
        Prompts for that dataset's evaluation split.

    Notes
    -----
    HarmBench uses the DirectRequest test split, which is the benchmark's
    harmful behavior list. The HumanJailbreaks config is a separate set of
    already wrapped attack prompts, and this loader does not include it.
    AdvBench has a single train split of 520 prompts. AgentHarm uses the
    public harmful test split.
    """
    spec = SPECS.get(dataset_name)
    if spec is None:
        known = ", ".join(DATASET_NAMES)
        raise SystemExit(f"Unknown dataset {dataset_name}. Known datasets: {known}.")
    if spec.config is None:
        rows = load_dataset(spec.repo, split=spec.split)
    else:
        rows = load_dataset(spec.repo, spec.config, split=spec.split)
    if dataset_name == "harmbench":
        return [_harmbench_example(row) for row in rows]
    if dataset_name == "advbench":
        return [_advbench_example(index, row) for index, row in enumerate(rows)]
    return [_agentharm_example(row) for row in rows]


def _harmbench_example(row: dict[str, str | None]) -> Example:
    behavior_id = str(row["BehaviorID"])
    prompt = harmbench_prompt(str(row["Behavior"]), row.get("ContextString"))
    _require_prompt("harmbench", behavior_id, prompt)
    return Example(
        example_id=behavior_id,
        prompt=prompt,
        metadata={
            "functional_category": str(row.get("FunctionalCategory") or ""),
            "semantic_category": str(row.get("SemanticCategory") or ""),
            "tags": str(row.get("Tags") or ""),
        },
    )


def _advbench_example(index: int, row: dict[str, str]) -> Example:
    example_id = f"advbench-{index}"
    prompt = str(row["prompt"]).strip()
    _require_prompt("advbench", example_id, prompt)
    return Example(example_id=example_id, prompt=prompt, metadata={})


def _agentharm_example(row: dict[str, str]) -> Example:
    example_id = str(row["id"])
    prompt = str(row["prompt"]).strip()
    _require_prompt("agentharm", example_id, prompt)
    return Example(
        example_id=example_id,
        prompt=prompt,
        metadata={
            "name": str(row.get("name") or ""),
            "category": str(row.get("category") or ""),
            "id_original": str(row.get("id_original") or ""),
        },
    )


def _require_prompt(dataset_name: str, example_id: str, prompt: str) -> None:
    if not prompt:
        raise ValueError(f"{dataset_name} example {example_id} has an empty prompt")
