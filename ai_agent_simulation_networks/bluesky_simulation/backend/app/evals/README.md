# Evals for Bluesky Simulation Backend

This package uses Opik’s pre-built evaluation metrics to score each agent turn and to run deterministic regression suites.

## Modules

- `opik_metrics.py`: Wraps Opik’s built-in metrics ([Usefulness, Moderation, Structured Output Compliance](https://www.comet.com/docs/opik/evaluation/metrics/overview/)).
  - Reuses the `opik.evaluation.metrics` implementations so we get maintained, first-party scoring.
  - Creates a dedicated `opik_metrics` span per agent-turn with structured results.

- `suite.py`: Deterministic offline eval suite for regression testing.
  - Replays canned bios/feeds, then pipes outputs through the same Opik metrics.
  - Exposed via `POST /eval/run`.

## How it integrates

- In `app/simulation.py`:
  - Each agent turn calls `score_with_opik_metrics(...)`, which runs Usefulness, Moderation, and Structured Output Compliance for like/draft responses.
  - Results appear as child spans beneath each agent in Opik.

- In `app/main.py`:
  - `POST /eval/run` executes the offline suite (`run_eval_suite`) and records the metrics.

## Usage

1. Ensure Opik is configured (local or cloud) via environment variables (see project README).
2. Run a simulation step to generate evals for each agent-turn:
   - `POST /simulation/step`
3. Run the offline deterministic eval suite:
   - `POST /eval/run`
4. Inspect the `opik_metrics` spans in Opik; filter by metric name (usefulness/moderation/structured_output).

## Extending

- Swap in any additional built-in metrics (Hallucination, Agent Task Completion, etc.) by importing them in `opik_metrics.py`.
- Expand `EVAL_CASES` in `suite.py` for broader regression coverage.
