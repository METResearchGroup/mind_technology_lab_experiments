# Step 7: Fit thresholds, metrics, figures, and S3 upload

The implementer turns saved prediction files from step 6 into development-tuned thresholds, full metrics (including stack policies), eight figure PNGs, an updated run manifest, and an S3 mirror of the experiment tree. This step does not call providers and does not rescore rows.

## Scope

- **Depends on:** step 6 (`outputs/predictions/{run_id}/`, `cache/responses.db`, and example rows under `data/records/`).
- **Caller order:** `scripts/run_metrics.py`, then `scripts/upload_s3.py`.
- **In scope:** `policies/union.py`, `policies/intersection.py`, `policies/cascade.py`; `shared/metrics.py`; `shared/thresholds.py`; metrics JSON; eight committed figure PNGs; manifest fields for this run; S3 upload per proposal section 5.
- **Out of scope:** New arms, edits to confirmed question templates, pytest or a `tests/` directory, any new TypeSafe or Cloudflare scoring, new guardrail API calls, and re-running `run_score.py` except to fix a blocking bug in step 6 outputs.

Proposal mapping: `proposal.md` section 5, section 6 (RQ1 through RQ6), section 7 (eight figures), Decisions made item 6 (OpenAI Moderation holdout), section 10 step 7.

## Files to inspect

- `/workspace/docs/plans/2026-10-19_safety-decision-model-benchmark_a7c3e1/proposal.md` (sections 5, 6, 7, 10 step 7, Decisions made)
- `/workspace/docs/plans/2026-10-19_safety-decision-model-benchmark_a7c3e1/plan.md` (step 7 row in the inputs/outputs table)
- `/workspace/experiments/speedup_jev_2026_09_23/scripts/upload_s3.py` (`BUCKET`, `PREFIX`, `SKIP_DIR_NAMES`, `SKIP_FILE_NAMES`, `s3_key_for_local_path`, `UPLOAD_COMPLETE_LINE`)
- `/workspace/experiments/moral_outrage_classification_2026_09_19/scripts/upload_s3.py` (same upload pattern)
- `experiments/safety_decision_models_2026_10_19/shared/records.py` (`PredictionRecord`, `ExampleRecord`)
- `experiments/safety_decision_models_2026_10_19/outputs/predictions/{run_id}/{arm}/{dataset}.parquet` and matching `.jsonl` from step 6
- `experiments/safety_decision_models_2026_10_19/data/records/{dataset}.parquet` (gitignored gold labels and splits)
- `experiments/safety_decision_models_2026_10_19/configs/study.json` (prices, region, pins)
- `experiments/safety_decision_models_2026_10_19/.gitignore` (metrics and manifests ignored; figures committed)
- Public harness reference only: `jev_benchmarking/metrics.py` and `jev_benchmarking/thresholds.py` (threshold grid behavior; harness is not vendored)

## Files allowed to change

- `experiments/safety_decision_models_2026_10_19/policies/union.py` (create or implement)
- `experiments/safety_decision_models_2026_10_19/policies/intersection.py` (create or implement)
- `experiments/safety_decision_models_2026_10_19/policies/cascade.py` (create or implement)
- `experiments/safety_decision_models_2026_10_19/shared/metrics.py` (create or implement)
- `experiments/safety_decision_models_2026_10_19/shared/thresholds.py` (create or implement)
- `experiments/safety_decision_models_2026_10_19/scripts/run_metrics.py` (create or implement)
- `experiments/safety_decision_models_2026_10_19/scripts/upload_s3.py` (create or implement)
- `experiments/safety_decision_models_2026_10_19/outputs/metrics/{run_id}.json` (gitignored; written by `run_metrics.py`)
- `experiments/safety_decision_models_2026_10_19/outputs/figures/{run_id}/*.png` (committed; exactly eight PNG files)
- `experiments/safety_decision_models_2026_10_19/outputs/manifests/{run_id}.json` (gitignored; finalize or update with metrics-run metadata)

## Files forbidden to change

- `tests/` (must not exist; do not create)
- Confirmed templates under `experiments/safety_decision_models_2026_10_19/data/templates/{dataset}.json` (archives under `data/templates/archive/` are also frozen for this run)
- `experiments/safety_decision_models_2026_10_19/scorers/` and `experiments/safety_decision_models_2026_10_19/datasets/` except a one-line import fix that blocks reading predictions
- Step 6 prediction parquet/jsonl contents (fix scoring in step 6, not here)
- Adding arms beyond `jev`, `clef`, `clef-flash`, and `guardrails`
- Plan files under `/workspace/docs/plans/2026-10-19_safety-decision-model-benchmark_a7c3e1/` except this step file when explicitly tasked

## Work

1. **Resolve `run_id`.** Use the same `run_id` as step 6 predictions, or allocate one at metrics start with form `{YYYYMMDD}T{HHMMSS}Z_{8 hex characters}` where the 8 hex characters hash dataset revisions, template versions, and the arm list (proposal section 5). Record it in `outputs/manifests/{run_id}.json`.

2. **Load inputs without rescoring.** Read `PredictionRecord` rows from `outputs/predictions/{run_id}/{arm}/{dataset}.parquet` (and join gold labels from `data/records/{dataset}.parquet` by `example_id` when metrics need labels). Do not call `DecisionScorer` or providers.

3. **Implement `shared/thresholds.py`.** Fit thresholds on development splits only. Target a **5% false-positive budget** on development items with `is_benign_known` true (proposal section 6, RQ2 and RQ5). Sets with no benign class do not set that budget. Always retain **threshold 0.5** as a reported operating point alongside tuned values.
   - **OpenAI Moderation:** fit the tuned threshold on the hash-stable **20% holdout** (proposal section 4, Decisions made item 6). **Exclude that holdout from the tuned test number.** The harness check at 0.5 on all 1,680 rows remains the step 4 number in `RESULTS.md`; do not overwrite it with tuned-test metrics.
   - **Prompt injections and JailbreakBench:** fewer than 200 labeled development items; **stay at 0.5 only** for tuned reporting, with AUROC as the threshold-free metric (proposal section 6, RQ2).
   - **GoEmotions:** optional per-label grid as in Deußer et al. (step 0.01) when implementing RQ2; document which split counts as development.
   - **Cascade:** fit `t_high` and `t_low` under the same 5% false-positive budget on development (proposal section 3 stack policies).

4. **Implement stack policies** in `policies/union.py`, `policies/intersection.py`, and `policies/cascade.py`. Each function takes saved `PredictionRecord` rows (plus fitted thresholds and guardrail strength) and returns a per-row block decision. They **do not** write prediction files. Stack numbers are aggregated into `outputs/metrics/{run_id}.json` only (proposal section 5).
   - **Union:** block if the guardrail blocks at the chosen strength or `P(harm) >= t`.
   - **Intersection:** block if the guardrail blocks and `P(harm) >= t`.
   - **Cascade:** block if `P(harm) >= t_high`; allow if `P(harm) <= t_low`; otherwise use the guardrail block decision.
   - Evaluate stacks for each decision model (`jev`, `clef`, `clef-flash`) paired with the saved guardrail bands.

5. **Implement `shared/metrics.py`.** Compute primary metrics per dataset (proposal section 3 table), plus ECE (15 equal-width bins), Brier, AUROC, AUPRC, selective prediction at 80% and 50% coverage, and risk-coverage AUC where proposal section 6 requires them. **RQ1:** 95% percentile bootstrap over items, 500 resamples; Clef vs Jev difference counts only when intervals do not overlap. **RQ3:** false-positive rate on JailbreakBench benign and XSTest `prompt_safe`; block rate by GoEmotions and Emotion labels (not labeled false positives). **RQ4:** miss and false-positive rate per guardrail strength (low, medium, high) using the published crosswalk. **RQ5:** miss vs false-positive for model alone, guardrail alone, and the three policies on sets with both harmful and benign classes. **RQ6:** median and p95 latency and cost per 1,000 prompts from billed units in prediction rows. **Do-Not-Answer:** detection rate overall and **aggregates by risk area and by type of harm** in the metrics JSON (no question text).

6. **Implement `scripts/run_metrics.py`.** Orchestrate threshold fit, policy evaluation, metric computation, figure generation, and manifest update. Write `outputs/metrics/{run_id}.json` with arms, stacks, thresholds (0.5 and tuned), bootstrap intervals, and Do-Not-Answer aggregates.

7. **Write eight figure PNGs** under `outputs/figures/{run_id}/` per proposal section 7 (committed to git):
   1. Miss rate vs false-positive rate (pooled benign vs matched harmful; all arms and stack policies).
   2. Reliability diagrams (`P(yes)` in 15 bins; Jev, Clef, Clef-flash; no guardrail bands).
   3. Threshold curves (ToxicChat jailbreak, ToxiGen, prompt injections; F1 and recall/FPR panels; marks at 0.5 and tuned threshold).
   4. Guardrail band vs dataset label (six filters; explicit empty self-harm row).
   5. Selective prediction (coverage vs miss rate or accuracy; 50% and 80% guides).
   6. Block rate by GoEmotions label (28 labels; Jev tuned, Clef tuned, Guardrails medium).
   7. Latency and cost vs miss rate (median latency, miss rate, cost per 1k prompts).
   8. Cascade flowchart (block / allow / ask guardrail; no numeric data required).

8. **Implement `scripts/upload_s3.py`.** Mirror the speedup experiment upload pattern with this experiment's prefix and Do-Not-Answer exclusions (below). Print the completion line exactly as in **Commands**.

## Interfaces

**Input contract:** `PredictionRecord` is the only scorer-side input to policies and metrics (proposal section 4). Fields: `example_id`, `arm`, `model_version`, `template_version`, `probability`, `band`, `raw_response`, `latency_ms`, `billed_units`, `error_status`. Gold labels come from gitignored `ExampleRecord` parquet on disk; do not reload Hugging Face rows for scoring.

**Policy contract (read predictions only):**

```python
def union_decisions(
    predictions: list[PredictionRecord],
    *,
    threshold: float,
    guardrail_strength: str,
) -> list[bool]: ...


def intersection_decisions(
    predictions: list[PredictionRecord],
    *,
    threshold: float,
    guardrail_strength: str,
) -> list[bool]: ...


def cascade_decisions(
    predictions: list[PredictionRecord],
    *,
    threshold_high: float,
    threshold_low: float,
    guardrail_strength: str,
) -> list[bool]: ...
```

Exact names may differ; behavior must match proposal section 3 stack policies. Guardrail "blocks" applies AWS strength rules to stored bands (`NONE` < `LOW` < `MEDIUM` < `HIGH`).

**Threshold contract:** `shared/thresholds.py` exposes functions that return fitted `t`, and for cascade `t_high` and `t_low`, plus the fixed `0.5` report. OpenAI Moderation tuned fit uses only the hash-stable 20% development holdout; test metrics for tuned thresholds exclude those ids.

**Metrics output:** `outputs/metrics/{run_id}.json` includes per-dataset primary metrics, calibration stats, bootstrap intervals, stack policy miss/FPR pairs, guardrail strengths, latency/cost summaries, and Do-Not-Answer aggregates by risk area and type of harm. Stack policies do not have separate prediction paths.

**Upload contract:**

```python
BUCKET = "mind-technology-lab-experiments"
PREFIX = "experiments/safety_decision_models_2026_10_19/"
SKIP_DIR_NAMES = {".venv", "__pycache__", ".pytest_cache", ".git"}
SKIP_FILE_NAMES = {".env"}
```

Key for each uploaded file: `PREFIX + path.relative_to(experiment_root).as_posix()` (same as `s3_key_for_local_path` in speedup `upload_s3.py`).

Additionally **skip** every local path that holds Do-Not-Answer question text:

- `data/snapshots/do_not_answer/` (any `rev_{commit}.parquet` under that dataset)
- `data/records/do_not_answer.parquet`
- Cache entries in `cache/responses.db` whose payload stores Do-Not-Answer question text (implement a filter in `iter_upload_paths` or equivalent)

**S3 tree** (objects under `s3://mind-technology-lab-experiments/experiments/safety_decision_models_2026_10_19/`):

```text
data/snapshots/{dataset}/rev_{commit}.parquet
data/records/{dataset}.parquet
cache/responses.db
outputs/predictions/{run_id}/{arm}/{dataset}.parquet
outputs/predictions/{run_id}/{arm}/{dataset}.jsonl
outputs/metrics/{run_id}.json
outputs/figures/{run_id}/
outputs/manifests/{run_id}.json
```

Do-Not-Answer raw text paths are omitted; aggregates by risk area and type of harm appear only inside `outputs/metrics/{run_id}.json`.

## Commands

From the experiment root:

```bash
cd experiments/safety_decision_models_2026_10_19 && uv run python scripts/run_metrics.py && uv run python scripts/upload_s3.py
```

Expected after `run_metrics.py`: `outputs/metrics/{run_id}.json` exists; eight PNG files under `outputs/figures/{run_id}/`; `outputs/manifests/{run_id}.json` updated.

Expected final line from `upload_s3.py`:

```text
UPLOAD COMPLETE s3://mind-technology-lab-experiments/experiments/safety_decision_models_2026_10_19/
```

Verify Do-Not-Answer text is not on S3 (region `us-east-2`, using the same key resolution as upload):

```bash
cd experiments/safety_decision_models_2026_10_19 && uv run python -c "
import boto3
from shared.secrets import build_boto3_session
prefix = 'experiments/safety_decision_models_2026_10_19/'
session = build_boto3_session()
s3 = session.client('s3', region_name='us-east-2')
paginator = s3.get_paginator('list_objects_v2')
bad = []
for page in paginator.paginate(Bucket='mind-technology-lab-experiments', Prefix=prefix):
    for obj in page.get('Contents', []):
        k = obj['Key']
        if 'do_not_answer' in k and ('snapshots' in k or 'records' in k):
            bad.append(k)
print('FORBIDDEN_KEYS', len(bad))
assert len(bad) == 0
"
```

Expected: `FORBIDDEN_KEYS 0` and exit code 0.

Local artifact check:

```bash
cd experiments/safety_decision_models_2026_10_19 && RUN_ID="$(ls -1 outputs/metrics | head -1)" && test -f "outputs/metrics/${RUN_ID}.json" && test "$(find outputs/figures/${RUN_ID} -name '*.png' | wc -l)" -eq 8 && echo ok
```

Expected output: `ok`

## Smoke check

- **No new provider smoke.** Steps 3 and 4 already validated live calls; step 7 is offline on saved predictions.
- **Pass means:**
  - Exactly **eight** PNG files exist under `outputs/figures/{run_id}/`.
  - `outputs/metrics/{run_id}.json` exists and includes stack policy sections and Do-Not-Answer aggregates (not raw question text).
  - Listing the S3 prefix shows uploaded metrics, figures, predictions, manifests, cache, and non-Do-Not-Answer data paths, and **does not** list a Do-Not-Answer snapshot, records file, or question-text cache object.
- **No pytest** for this study.

## Cost and credentials

- **AWS S3:** `LAB_AWS_ACCESS_KEY_ID` and `LAB_AWS_ACCESS_KEY_SECRET` (same resolution as `experiments/speedup_jev_2026_09_23/shared/secrets.py`), region **`us-east-2`**.
- **No new TypeSafe or Cloudflare calls** in this step; no new `ApplyGuardrail` calls.
- **Cost:** S3 storage and PUT traffic only. Model spend was incurred in step 6; the **bill from step 6 replaces** the planning estimate of under US$50 in proposal section 10.

## Done when

1. `policies/union.py`, `policies/intersection.py`, and `policies/cascade.py` implement the three stack rules on `PredictionRecord` rows only and do not create prediction files.
2. `shared/thresholds.py` and `shared/metrics.py` implement development tuning with a 5% false-positive budget where applicable, 0.5 reporting everywhere relevant, OpenAI Moderation tuned fit on the 20% holdout with holdout excluded from tuned test metrics, and prompt injections plus JailbreakBench held at 0.5 for tuned numbers.
3. `scripts/run_metrics.py` writes `outputs/metrics/{run_id}.json` and eight committed PNGs under `outputs/figures/{run_id}/`, and updates `outputs/manifests/{run_id}.json` for the same `run_id`.
4. `scripts/upload_s3.py` uploads the section 5 tree to `s3://mind-technology-lab-experiments/experiments/safety_decision_models_2026_10_19/` with standard skip dirs/files and Do-Not-Answer text exclusions, and prints `UPLOAD COMPLETE s3://mind-technology-lab-experiments/experiments/safety_decision_models_2026_10_19/`.
5. Smoke checks above pass without pytest and without rescoring.
