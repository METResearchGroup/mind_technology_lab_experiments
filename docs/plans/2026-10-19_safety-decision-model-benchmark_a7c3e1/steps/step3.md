# Step 3: Run the 20-item smoke test

## Scope

- **Depends on:** Step 1 (scaffold, loaders, scorers, cache stub) and Step 2 (one confirmed template per dataset under `data/templates/{dataset}.json`).
- **Task:** Implement and run `experiments/safety_decision_models_2026_10_19/scripts/smoke.py` so 20 development `ExampleRecord` rows flow end to end through each decision arm, write predictions only into the gitignored cache, verify cache hits on a second pass, and compare Jev smoke metrics to the published harness primary metric for the overlapping datasets represented in the 20 items.
- **Execution order (plan dependencies):** Step 5 creates the numbered guardrail in `us-east-2` after Step 4. Step 3 still ships one script that accepts all four arms (`jev`, `clef`, `clef-flash`, `guardrails`). For the first smoke pass in Step 3, run **Jev, Clef, and Clef-flash** only. Run the **Guardrails** arm with the same script **after Step 5** because detect-only `ApplyGuardrail` must return a band. Step 4 (harness check) may proceed once the three decision-model arms pass. Step 6 needs both the Step 3 decision-model smoke and the post-Step 5 Guardrails smoke.
- **Out of scope:** Full core-pack scoring (`run_score.py`), harness check on six full datasets (Step 4), guardrail creation (Step 5), pytest, any `tests/` directory, committing predictions or Do-Not-Answer question text.

Proposal mapping: section 4 (smoke paragraph under Storage and checks), section 5 (`scripts/smoke.py`), section 10 step 3.

## Files to inspect

- `/workspace/docs/plans/2026-10-19_safety-decision-model-benchmark_a7c3e1/proposal.md` (section 4 smoke, credentials, cache key, `PredictionRecord`; section 5 tree)
- `/workspace/docs/plans/2026-10-19_safety-decision-model-benchmark_a7c3e1/plan.md` (Step 3 summary, dependencies, secrets table)
- `experiments/safety_decision_models_2026_10_19/scripts/smoke.py` (stub from Step 1)
- `experiments/safety_decision_models_2026_10_19/shared/records.py` (`ExampleRecord`, `QuestionSpec`, `PredictionRecord`)
- `experiments/safety_decision_models_2026_10_19/shared/cache.py` (cache key and `cache/responses.db`)
- `experiments/safety_decision_models_2026_10_19/shared/metrics.py` (primary metric for Jev harness comparison on smoke rows)
- `experiments/safety_decision_models_2026_10_19/data/templates/{dataset}.json` (template version is hash of file)
- `experiments/safety_decision_models_2026_10_19/configs/study.json` (model pins, region `us-east-2`, optional guardrail id placeholder until Step 5)
- `experiments/safety_decision_models_2026_10_19/scorers/jev.py`, `scorers/clef.py`, `scorers/guardrails.py` (call only; do not edit in this step)
- `experiments/safety_decision_models_2026_10_19/datasets/*.py` (how to draw 20 development items)
- `experiments/speedup_jev_2026_09_23/scripts/smoke.py` (entry style)
- `experiments/speedup_jev_2026_09_23/shared/secrets.py` (`load_typesafe_api_key`, `resolve_aws_access_keys`, region `us-east-2`)
- Public harness metric definitions: https://github.com/AppliedMachineLearning-Lab/jev-benchmarking (`jev_benchmarking/metrics.py`, overlapping tasks in `tasks/safety.py` and `tasks/classification.py`; not vendored)

## Files allowed to change

- `experiments/safety_decision_models_2026_10_19/scripts/smoke.py` only

Do not change scorers except by importing and calling `DecisionScorer.score`. Do not add pytest or a `tests/` directory.

## Files forbidden to change

- Everything under `experiments/safety_decision_models_2026_10_19/` except `scripts/smoke.py`
- Plan and proposal files under `/workspace/docs/plans/2026-10-19_safety-decision-model-benchmark_a7c3e1/`
- Root `pyproject.toml` workspace membership and ruff/pyright excludes (Step 1)
- Any path that would commit Do-Not-Answer question text, API keys, or raw smoke predictions

## Work

1. Replace the Step 1 stub in `scripts/smoke.py` with a CLI that:
   - Loads 20 development `ExampleRecord` rows (same development pool Step 2 used for template confirmation; stable selection documented in the script or `configs/study.json` smoke section if present).
   - For each requested arm, loads `QuestionSpec` from `data/templates/{dataset}.json` per row's `dataset` field and `template_version` from the template file hash.
   - Calls the matching scorer's `score(records, question)` once for the batch of 20 (or per dataset subgroup if the scorers require one question spec per dataset).
   - Asserts every `PredictionRecord` has the expected fields; decision-model arms must have non-null `probability`; Guardrails must have non-null `band`.
   - Runs the **same** 20 items a second time and proves each lookup uses `cache/responses.db` with **no new provider HTTP/API call** (log or count provider calls; second pass must be cache-only).
   - For Jev rows, computes the same **primary metric** as the published harness check for each dataset present in the 20 items and checks comparability (metric code path must run; stop if comparison to published intervals is impossible because templates or labels do not align).
2. **First pass (Step 3):** `uv run python scripts/smoke.py` with arms `jev`, `clef`, `clef-flash` (default or explicit flags). Clef and Clef-flash share `scorers/clef.py`; arm name on each prediction distinguishes them.
3. **Guardrails arm:** If the numbered guardrail from Step 5 does not exist yet, Step 3 may read a guardrail identifier from `configs/study.json` only when that id already resolves in `us-east-2`. Otherwise skip Guardrails in Step 3 and document that Step 5 must create the resource, then re-run `scripts/smoke.py` for arm `guardrails` before Step 6. Smoke for Guardrails requires detect-only `ApplyGuardrail` with filter action `NONE` and a non-empty band on every row.
4. **Truncation and errors (smoke must surface scorer behavior, not rewrite scorers):**
   - Clef: mark `error_status` `truncated` when context exceeds 64,000 tokens (Workers AI shortens `state` but still answers).
   - Clef-flash: same with limit 24,576 tokens.
   - Jev: record provider error `max_tokens_exceeded` on context overflow.
   - Guardrails: one detect-only `ApplyGuardrail` per row; strengths are derived from bands after the call, not separate paid calls in smoke unless detect mode omits the band (Step 5 handles version fallback).
5. Keep all smoke `PredictionRecord` payloads in gitignored storage (`cache/responses.db` and any smoke-local paths under `cache/` or `outputs/` if the stub writes there). Do not commit predictions.

**Stop conditions (non-zero exit):**

- Any Jev, Clef, or Clef-flash row has empty or missing `probability`.
- Any Guardrails row has empty or missing `band`.
- Second pass misses the cache or triggers a new provider call.
- Jev smoke metric cannot be compared with the published harness metric for the datasets in the 20 items.

## Interfaces

| Piece | Contract |
| --- | --- |
| Input rows | `list[ExampleRecord]` from dataset loaders (20 development items) |
| Question | `QuestionSpec` parsed from `experiments/safety_decision_models_2026_10_19/data/templates/{dataset}.json` |
| Scoring | `DecisionScorer.score(records, question) -> list[PredictionRecord]` on `scorers/jev.py`, `scorers/clef.py`, `scorers/guardrails.py` |
| Output | `PredictionRecord` with `example_id`, `arm`, `model_version`, `template_version`, `probability` or `band`, `raw_response`, `latency_ms`, `billed_units`, `error_status` |
| Cache key | `hash(arm, model_version, template_version, example_id)` stored in `cache/responses.db` |
| Clef HTTP body | `model`, `state`, `questions` object keyed by question id (not a list) |
| Arms | `jev`, `clef`, `clef-flash`, `guardrails` (CLI accepts all four; see Scope for run order) |

## Commands

Working directory for every command:

```text
cd /workspace/experiments/safety_decision_models_2026_10_19
```

Install dependencies (once, if not already done from Step 1):

```bash
uv sync
```

Step 3 smoke (decision models; required before Step 4):

```bash
uv run python scripts/smoke.py
```

If the script uses explicit arm flags, equivalent:

```bash
uv run python scripts/smoke.py --arms jev clef clef-flash
```

After Step 5 (guardrail exists and `configs/study.json` or manifest holds the version id):

```bash
uv run python scripts/smoke.py --arms guardrails
```

Expected behavior:

- First run per arm: provider calls for 20 items (about 60 calls for three arms in Step 3).
- Second run for the same arm and same 20 items: cache hits only, zero new provider calls.
- Process exits 0 only when stop conditions are all clear.

## Smoke check

This step **is** the smoke check defined in proposal section 4:

- 20 development items, end to end, once per arm on the first provider pass.
- Jev, Clef, and Clef-flash return a non-empty probability on every row.
- Guardrails returns a non-empty band on every row when that arm is run (post-Step 5).
- A second pass of the same 20 items per arm hits `cache/responses.db` and makes no new provider call.
- Jev smoke rows use the same primary metric as the published harness check so a broken template fails before the full run.

The implementer records pass/fail in the terminal log or a local gitignored log under `cache/`; do not commit smoke predictions.

## Cost and credentials

**Region:** `us-east-2` for Secrets Manager, Bedrock `ApplyGuardrail`, and guardrail resources.

**Cost:** 20 items times 4 arms is about 80 provider requests on the first pass across all arms, plus a cache-hit rerun that adds **no** provider calls. In Step 3 only three arms run first (about 60 requests). This is a small fraction of the under US$50 planning budget for the core pack.

**Credentials (never printed, never committed):**

| Purpose | Source | Fields / env |
| --- | --- | --- |
| Jev / TypeSafe | Secret `jev-typesafe-api-key` via `load_typesafe_api_key` in `experiments/speedup_jev_2026_09_23/shared/secrets.py` (reuse pattern in this study's shared secrets if Step 1 copied it) | JSON `TYPESAFE_API_KEY` |
| Clef / Clef-flash | Secret `cloudflare-workers-ai` in `us-east-2` | `account_id`, `api_token` |
| Guardrails / AWS | `LAB_AWS_ACCESS_KEY_ID` and `LAB_AWS_ACCESS_KEY_SECRET` (then standard AWS env names per speedup secrets helper) | `bedrock:ApplyGuardrail`, guardrail create in Step 5 |
| Gated Hugging Face rows | Secret `hf-token` | Only if one of the 20 development items requires a gated dataset |

Do not upload or commit Do-Not-Answer question text. Smoke cache and any snapshot rows that contain it stay gitignored.

## Done when

1. `experiments/safety_decision_models_2026_10_19/scripts/smoke.py` implements the flow above and is the only file changed in this step.
2. From `experiments/safety_decision_models_2026_10_19/`, `uv run python scripts/smoke.py` exits 0 for arms `jev`, `clef`, and `clef-flash` on 20 development items, with non-empty probabilities, Jev harness-metric comparability, and cache-only second pass.
3. No committed predictions; `cache/responses.db` may exist locally and is gitignored.
4. Guardrails: either (a) skipped in Step 3 with guardrail id pending Step 5, or (b) if a valid id is already in `configs/study.json`, smoke passes with non-empty bands. In all cases, **before Step 6**, the same script has been re-run for arm `guardrails` after Step 5 creates the numbered guardrail and the detect-only call returns a band on all 20 items, with cache hit on rerun.
5. Step 4 can start after item 2; Step 6 waits for item 4 as well as Step 5 crosswalk work.
