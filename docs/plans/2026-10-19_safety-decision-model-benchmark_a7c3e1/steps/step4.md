# Step 4: Jev harness check on six overlapping sets

## Scope

- **Depends on:** Step 3 (`scripts/smoke.py` passed for all four arms with cache hit on rerun).
- **Caller:** `experiments/safety_decision_models_2026_10_19/scripts/run_score.py`, limited to arm `jev` and datasets `toxigen`, `openai_moderation`, `toxicchat`, `prompt_injections`, `go_emotions`, `emotion`.
- **Task:** Score every test (or full-set) row for those six datasets with TypeSafe Jev model `jev-1.13.0`, using the confirmed templates from Step 2. Compute each dataset's **primary metric** at threshold **0.5** (no development-tuned thresholds; tuning is Step 7). Compare each number to the published figures in [proposal.md](../proposal.md) section 3 ("Published Jev numbers we will use as a harness check"). Write the comparison into the harness-check table in `RESULTS.md`.
- **Stop rule:** If any primary metric for these six sets falls **outside** its published 95% interval (where the paper gives an interval), **stop the study** and fix the template or harness before Clef, Clef-flash, or Guardrails are scored. Do not reinterpret intervals or tune thresholds to pass this step.
- **Out of scope:** Do-Not-Answer and every other core-pack dataset; arms `clef`, `clef-flash`, and `guardrails`; threshold fitting; metrics JSON, figures, S3 upload; creating or editing question templates; pytest or any `tests/` directory.

## Files to inspect

- [../proposal.md](../proposal.md) section 3 (published Jev numbers and intervals), section 4 (loaders, scorers, cache, OpenAI Moderation harness rule), section 5 (`run_id`, prediction paths, manifest), section 10 step 4.
- [../plan.md](../plan.md) Step 4 and the dependency table (Step 4 inputs/outputs).
- `experiments/safety_decision_models_2026_10_19/scripts/run_score.py` (CLI and Jev-only path for this step).
- `experiments/safety_decision_models_2026_10_19/scorers/jev.py` (`DecisionScorer` for Jev).
- `experiments/safety_decision_models_2026_10_19/shared/records.py` (`ExampleRecord`, `PredictionRecord`, `QuestionSpec`).
- `experiments/safety_decision_models_2026_10_19/shared/metrics.py` (primary metrics aligned with Deußer et al.).
- `experiments/safety_decision_models_2026_10_19/shared/cache.py` (cache key and `cache/responses.db`).
- `experiments/safety_decision_models_2026_10_19/data/templates/{dataset}.json` for the six datasets (read-only in this step).
- `experiments/speedup_jev_2026_09_23/shared/secrets.py` (`load_typesafe_api_key`).
- Public harness reference (not vendored): `jev_benchmarking/tasks/safety.py`, `jev_benchmarking/tasks/classification.py`, `jev_benchmarking/metrics.py` at https://github.com/AppliedMachineLearning-Lab/jev-benchmarking .

## Files allowed to change

- `experiments/safety_decision_models_2026_10_19/RESULTS.md` **only** the harness-check table (add or update rows for this run; do not edit other sections).
- Gitignored outputs for this run:
  - `experiments/safety_decision_models_2026_10_19/outputs/predictions/{run_id}/jev/*` (`.parquet` and `.jsonl` per dataset).
  - `experiments/safety_decision_models_2026_10_19/outputs/manifests/{run_id}.json` (dataset revisions, template versions, arm list `["jev"]`, model pin `jev-1.13.0`, region `us-east-2`, prices from `configs/study.json`).
- `cache/responses.db` updates from scoring (gitignored; expected).

## Files forbidden to change

- Any file under `experiments/safety_decision_models_2026_10_19/data/templates/` (including `archive/`).
- Scorer modules other than bugfixes required to complete this step (prefer fixing templates or metrics definitions first).
- Arms `clef`, `clef-flash`, `guardrails`; policies; `scripts/smoke.py`; `scripts/run_metrics.py`; `scripts/upload_s3.py`.
- Predictions or manifests for other `run_id` values unless intentionally superseding a failed harness attempt (document the new `run_id` in `RESULTS.md`).
- Plan or proposal markdown under `docs/plans/`.
- Root workspace, other experiments, `tests/`, pytest config, or CI workflows.

## Work

1. **Prerequisite:** Confirm Step 3 is recorded as passed (smoke log or `RESULTS.md` note). Do not start paid Jev scoring if Step 3 failed.
2. **Allocate `run_id`:** At UTC start, set `run_id` to `{YYYYMMDD}T{HHMMSS}Z_{8 hex characters}`. The 8 hex characters are a deterministic hash of pinned Hugging Face revision per dataset, template version hash per dataset, and the arm list `["jev"]` for this run. Write the same `run_id` into `outputs/manifests/{run_id}.json`.
3. **Run scoring:** Run `run_score.py` with `--arm jev` and `--datasets toxigen,openai_moderation,toxicchat,prompt_injections,go_emotions,emotion` (see Commands). Model version must be `jev-1.13.0`. Use confirmed `QuestionSpec` JSON per dataset. Respect the request cache so retries do not double-bill.
4. **Splits and row counts (score all rows in the harness split):**
   - `toxigen`: test, 940 rows.
   - `openai_moderation`: **full set, 1,680 rows**, all scored at threshold **0.5** (Decisions made item 6; tuned holdout is Step 7 only).
   - `toxicchat`: test, 5,083 rows.
   - `prompt_injections`: test, 116 rows.
   - `go_emotions`: test, 5,427 rows.
   - `emotion`: test, 2,000 rows.
5. **Compute primary metrics at 0.5** (match proposal section 3 "Primary metrics, by dataset" and the published table):

   | Dataset | Primary metric for harness check | Published value | Published 95% interval (if given) |
   | --- | --- | --- | --- |
   | toxigen | Accuracy on the toxic label | 0.878 | 0.857 to 0.898 |
   | openai_moderation | Mean AUPRC across categories | 0.717 | 0.675 to 0.759 |
   | toxicchat | Toxicity positive-class F1 at 0.5 | 0.786 | (point value; compare to 0.786) |
   | toxicchat | Jailbreak positive-class F1 at 0.5 | 0.717 | (point value; compare to 0.717) |
   | prompt_injections | Accuracy | 0.741 | 0.664 to 0.828 |
   | go_emotions | Macro-F1 at 0.5 | 0.243 | (point value; compare to 0.243) |
   | emotion | Accuracy | 0.585 | 0.563 to 0.605 |

   Optional diagnostic columns in `RESULTS.md` (ECE, AUROC, Score Spearman for ToxiGen) may cite the same section 3 table but **pass/fail** for this step is on the primary metrics above. For ToxicChat and GoEmotions, where the paper quotes a point estimate at 0.5 without a bootstrap interval, treat equality within reasonable floating tolerance as inside the published figure; if implementation diverges materially, stop and debug like an interval miss.

6. **Interval check:** For each metric with a published interval, require `interval_low <= our_value <= interval_high`. If any check fails, **exit non-zero**, do not proceed to Step 5 or 6 for paid non-Jev arms, and record `FAIL` with observed value in `RESULTS.md` before fixing templates.
7. **On success:** Mark harness check `PASS` in `RESULTS.md`, list `run_id`, manifest path, and prediction paths under `outputs/predictions/{run_id}/jev/`.

## Interfaces

Reuse proposal section 4 types and cache rule (implemented in Step 1):

- **`ExampleRecord`:** `example_id`, `dataset`, `split`, `text`, `gold_labels`, `harm_category`, `is_benign_known`, `metadata`.
- **`QuestionSpec`:** Choice, Noul, or Score JSON matching `jev_benchmarking/tasks/base.py` shape; version is hash of `data/templates/{dataset}.json`.
- **`DecisionScorer`:** `score(records: list[ExampleRecord], question: QuestionSpec) -> list[PredictionRecord]`; Jev implementation in `scorers/jev.py`.
- **`PredictionRecord`:** `example_id`, `arm` (`jev`), `model_version` (`jev-1.13.0`), `template_version`, `probability`, `band`, `raw_response`, `latency_ms`, `billed_units`, `error_status`.
- **Cache key:** `hash(arm, model_version, template_version, example_id)` stored in `cache/responses.db`; identical retry must not call the provider.

### `run_score.py` CLI contract (Step 1 deliverable; this step is the first consumer)

| Flag | Required | Meaning |
| --- | --- | --- |
| `--arm` | yes | Single arm name. This step passes `jev`. Allowed repo-wide values remain `jev`, `clef`, `clef-flash`, `guardrails`. |
| `--datasets` | yes | Comma-separated short names with no spaces. This step: `toxigen,openai_moderation,toxicchat,prompt_injections,go_emotions,emotion`. |
| `--run-id` | optional | If omitted, allocate `{YYYYMMDD}T{HHMMSS}Z_{8 hex}` as above. If provided, must match manifest hash inputs. |
| `--threshold` | optional | Default `0.5` for harness metrics. **Do not** pass a tuned threshold in Step 4. |

**Behavior:** Load pinned rows from `data/records/` (or loaders), read template per dataset, call Jev scorer with rate limiting and retries per `experiments/moral_outrage_classification_2026_09_19/shared/engine_loop.py` pattern, write `outputs/predictions/{run_id}/jev/{dataset}.parquet` and `.jsonl`, update manifest, compute harness primary metrics (or emit predictions only and compute in a small harness helper; either way the numbers in `RESULTS.md` must match the saved predictions).

**Exit codes:** `0` when all interval checks pass; **non-zero** when any primary metric is outside its published interval or when scoring aborts (auth, rate limit exhaustion, revision mismatch).

## Commands

From the experiment root:

```bash
cd experiments/safety_decision_models_2026_10_19 && uv run python scripts/run_score.py --arm jev --datasets toxigen,openai_moderation,toxicchat,prompt_injections,go_emotions,emotion
```

**Expected behavior:**

- Creates or updates `outputs/manifests/{run_id}.json` with dataset commits, template versions, arms `["jev"]`, and `jev-1.13.0`.
- Writes six prediction partitions under `outputs/predictions/{run_id}/jev/`.
- Prints a short summary per dataset (row count, primary metric, interval bounds) and whether the harness check passed.
- **On interval miss:** prints which dataset and metric failed, writes `FAIL` to `RESULTS.md` if not already updated, exits with code **1** (or another non-zero code documented in `run_score.py`). **Do not** continue to Clef or Guardrails scoring until templates are fixed and Step 4 is re-run.
- **On pass:** exits **0**; Step 5 may start.

Optional verification (no pytest):

```bash
cd experiments/safety_decision_models_2026_10_19 && uv run python -c "
import json, glob, sys
ms = sorted(glob.glob('outputs/manifests/*.json'))[-1:]
assert ms, 'no manifest'
m = json.load(open(ms[0]))
assert m.get('arms') == ['jev'] or m.get('arm') == 'jev'
print('manifest ok', ms[0])
"
```

## Smoke check

Step 3 already validated 20 development items per arm end to end. **This step does not add a new smoke script and does not run pytest.**

Pass criterion for Step 4: the harness-check table in `experiments/safety_decision_models_2026_10_19/RESULTS.md` shows every primary metric for the six datasets **inside** the published interval (or on the published 0.5 point estimate where no interval is listed), with explicit `PASS` and the `run_id` used.

## Cost and credentials

- **Credential:** AWS Secrets Manager in `us-east-2`, secret `jev-typesafe-api-key`, JSON field `TYPESAFE_API_KEY`, via `load_typesafe_api_key` in `experiments/speedup_jev_2026_09_23/shared/secrets.py`. Region for the TypeSafe client matches `us-east-2` / study config.
- **Not required for these six sets:** `hf-token` (all six are public Hugging Face datasets without a gating form for this pack).
- **Not used in this step:** `cloudflare-workers-ai`, AWS Bedrock `ApplyGuardrail`, Clef, Guardrails spend.
- **Cost (Jev only):** Quote [proposal.md](../proposal.md) section 10 pricing table, not a new price: Jev `jev-1.13.0` at **US$0.042 per million input tokens**, output free. The full core pack at about 12.9M input tokens is about **US$0.54** for one Jev pass; this step scores six datasets only (subset of rows), so billed cost stays **well under** the study planning cap of **US$50**. Deußer et al. reported 346,009 requests and US$9.15 on their broader 37-dataset suite; this harness subset is much smaller.

## Done when

1. Step 3 is satisfied and documented.
2. `run_score.py` completed with `--arm jev` and the six dataset names; `outputs/manifests/{run_id}.json` exists with correct hash inputs and `jev-1.13.0`.
3. Predictions exist under `outputs/predictions/{run_id}/jev/` for all six datasets.
4. OpenAI Moderation harness metric used **all 1,680 rows at threshold 0.5** (no tuned threshold, no holdout exclusion in this step).
5. `RESULTS.md` harness-check table lists, per dataset: primary metric name, published value, interval (if any), observed value, `PASS` or `FAIL`, and `run_id`.
6. Every row shows `PASS` and the process exited **0**; otherwise the study **stopped** with `FAIL` and no Clef or Guardrails full-pack scoring until Step 4 is re-run after a template fix.
