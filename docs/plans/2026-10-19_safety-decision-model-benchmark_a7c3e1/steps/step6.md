# Step 6: Score the core pack through the cache

## Scope

- **Depends on:** Step 3 (20-item smoke passed) and Step 5 (numbered guardrail in `us-east-2`, crosswalk written, guardrail version id in manifest).
- **Caller:** `experiments/safety_decision_models_2026_10_19/scripts/run_score.py` (created in step 1).
- **Task:** Score every row in the core pack once per arm through `cache/responses.db`, writing gitignored prediction partitions under `outputs/predictions/{run_id}/`.
- **Arms (only these four):** `jev`, `clef`, `clef-flash`, `guardrails`. Do not score stack policies or any other arm in this step. Union, intersection, and cascade are step 7 only.
- **Datasets (eleven short names, one template each from step 2):** `toxigen`, `openai_moderation`, `toxicchat`, `prompt_injections`, `wildguardmix`, `do_not_answer`, `xstest`, `harmbench`, `jailbreakbench`, `go_emotions`, `emotion`.
- **Out of scope:** S3 upload (step 7), threshold fitting, metrics, figures, harness re-check (step 4), repeating the 20-item smoke as the gate (step 3), editing templates or the crosswalk, committing prediction files or Do-Not-Answer question text.

## Files to inspect

- `/workspace/docs/plans/2026-10-19_safety-decision-model-benchmark_a7c3e1/proposal.md` (sections 4, 5, 9, 10 step 6)
- `/workspace/experiments/safety_decision_models_2026_10_19/scripts/run_score.py`
- `/workspace/experiments/safety_decision_models_2026_10_19/shared/cache.py` (`ResponseCache`, cache key)
- `/workspace/experiments/safety_decision_models_2026_10_19/shared/records.py` (`ExampleRecord`, `PredictionRecord`, `QuestionSpec`)
- `/workspace/experiments/safety_decision_models_2026_10_19/scorers/jev.py`
- `/workspace/experiments/safety_decision_models_2026_10_19/scorers/clef.py` (arms `clef` and `clef-flash`)
- `/workspace/experiments/safety_decision_models_2026_10_19/scorers/guardrails.py`
- `/workspace/experiments/safety_decision_models_2026_10_19/datasets/*.py` (eleven loaders)
- `/workspace/experiments/safety_decision_models_2026_10_19/data/templates/{dataset}.json`
- `/workspace/experiments/safety_decision_models_2026_10_19/configs/study.json` (pins, prices, region; guardrail version id after step 5)
- `/workspace/experiments/speedup_jev_2026_09_23/shared/secrets.py` (TypeSafe and AWS key resolution)
- `/workspace/experiments/speedup_jev_2026_09_23/shared/rate_limiter.py` (`RequestStartLimiter`)
- `/workspace/experiments/moral_outrage_classification_2026_09_19/shared/engine_loop.py` (429 and 5xx retry pattern)

## Files allowed to change

- `/workspace/experiments/safety_decision_models_2026_10_19/scripts/run_score.py` if full-pack flags (`--arm`, `--dataset`, `--run-id`, or equivalent) are missing
- `/workspace/experiments/safety_decision_models_2026_10_19/scorers/clef.py` only if step 1 left a gap in truncation handling (`error_status` `truncated` when over limit)
- Gitignored paths only for this run:
  - `experiments/safety_decision_models_2026_10_19/cache/responses.db`
  - `experiments/safety_decision_models_2026_10_19/data/records/{dataset}.parquet`
  - `experiments/safety_decision_models_2026_10_19/data/snapshots/{dataset}/rev_{commit}.parquet`
  - `experiments/safety_decision_models_2026_10_19/outputs/predictions/{run_id}/{arm}/{dataset}.parquet`
  - `experiments/safety_decision_models_2026_10_19/outputs/predictions/{run_id}/{arm}/{dataset}.jsonl`
  - `experiments/safety_decision_models_2026_10_19/outputs/manifests/{run_id}.json` (append or refresh scoring metadata for this `run_id`)

## Files forbidden to change

- `/workspace/docs/plans/2026-10-19_safety-decision-model-benchmark_a7c3e1/` plan files (except this step file if the parent agent edits plans)
- `experiments/safety_decision_models_2026_10_19/tests/` (must not exist; do not create)
- `experiments/safety_decision_models_2026_10_19/data/templates/*.json` and `data/templates/archive/` (confirmed in step 2)
- The dataset-label-to-filter crosswalk and guardrail definition in `configs/study.json` beyond reading the version id from step 5
- Any git-tracked file that would embed Do-Not-Answer question text
- Root workspace CI, ruff, or pyright config except as already scoped in step 1

## Work

1. **Preflight:** Confirm step 3 smoke passed and step 5 manifest contains the guardrail version id. Load `configs/study.json` for model pins, template versions, dataset revisions, and region `us-east-2`. Refuse to start if a Hugging Face revision differs from the manifest (same rule as step 1).
2. **Allocate `run_id`:** `{YYYYMMDD}T{HHMMSS}Z_{8 hex characters}` in UTC. The hash covers dataset revisions, template versions, and the arm list (`jev`, `clef`, `clef-flash`, `guardrails`). Write or update `outputs/manifests/{run_id}.json` with those fields, prices, and region before scoring finishes.
3. **Load examples:** For each dataset, load scored split rows into `ExampleRecord` lists (from `data/records/` or loaders). Do-Not-Answer question text may exist only in the gitignored local cache for the run; never copy that text into a committed path.
4. **Score loop:** For each arm and each dataset, call the matching `DecisionScorer` with the confirmed `QuestionSpec` from `data/templates/{dataset}.json`. Respect per-provider `RequestStartLimiter`. On cache hit (key below), read the stored response and do not call the provider again.
5. **Write partitions:** After each arm and dataset completes, write both:
   - `outputs/predictions/{run_id}/{arm}/{dataset}.parquet`
   - `outputs/predictions/{run_id}/{arm}/{dataset}.jsonl`
   Row count must match the loader row count for that dataset split (HarmBench counts both configs; JailbreakBench both splits; XSTest unique prompts after dedupe).
6. **Truncation and errors:** Keep every row in the metric table. For Clef and Clef-flash, if token count exceeds 64,000 (`clef`) or 24,576 (`clef-flash`), set `error_status` to `truncated` (Workers AI shortens `state` and still returns an answer). For Jev, store provider error `max_tokens_exceeded` on HTTP 400 context overflow. Guardrails rows use `band` and `probability` null.
7. **Report:** When `--arm all` finishes, print total truncated row count across Clef and Clef-flash (and optionally Jev `max_tokens_exceeded` count). Do not upload to S3 in this step. Step 7 will mirror relative paths under `s3://mind-technology-lab-experiments/experiments/safety_decision_models_2026_10_19/`.

Expected partition count: 11 datasets times 4 arms equals 44 parquet files and 44 jsonl files for one full `run_id`.

## Interfaces

**Cache key** (same as proposal section 4): hash of `arm`, `model_version`, `template_version`, and `example_id`. A retry that finds the key must not issue a second provider call.

**Clef / Clef-flash request body** (object `questions`, not a list):

```python
{
    "model": "clef",  # or "clef-flash"
    "state": text,
    "questions": {
        "<question_id>": {
            "type": "noul" | "choice" | "score",
            "instructions": "...",
            "criteria": ... | None,
        },
    },
}
```

**Clef response fields:** `result.answers.<id>` (for example `{"type": "noul", "noul": 0.0039}`), `result.usage.input_tokens` for billed input tokens.

**Truncation:** Before the call or via `result.usage.input_tokens`, if over 64,000 (`clef`) or 24,576 (`clef-flash`), set `error_status` to `truncated`. Never leave `error_status` empty on an over-limit Clef row that was shortened.

**Jev:** On HTTP 400 context overflow, set `error_status` to `max_tokens_exceeded` (harness parity).

**Guardrails:** One detect-only `ApplyGuardrail` per example in `us-east-2`, content filters only, filter action `NONE`, using the numbered guardrail version id from step 5. `probability` is null; `band` is set from the returned filter bands. Low, medium, and high strength are derived from bands in step 7, not separate paid calls in this step unless step 5 already created three versions as fallback.

**PredictionRecord** (write one row per scored example):

| Field | Jev / Clef / Clef-flash | Guardrails |
| --- | --- | --- |
| `example_id` | required | required |
| `arm` | `jev`, `clef`, or `clef-flash` | `guardrails` |
| `model_version` | pin from manifest | guardrail version id |
| `template_version` | hash of template JSON | same |
| `probability` | from Noul/Choice/Score answer | `null` |
| `band` | `null` | `NONE` / `LOW` / `MEDIUM` / `HIGH` |
| `raw_response` | provider JSON | ApplyGuardrail payload |
| `latency_ms` | wall clock | wall clock |
| `billed_units` | tokens | text units |
| `error_status` | `null`, `truncated`, or `max_tokens_exceeded` | `null` or provider error |

## Commands

From the experiment root:

```bash
cd /workspace/experiments/safety_decision_models_2026_10_19 && uv run python scripts/run_score.py --arm all
```

Expected:

- Process exits 0 when all arms and datasets complete (or exits non-zero with a clear error if credentials, quota, or revision mismatch).
- Stdout includes a printed count of truncated rows (Clef and Clef-flash; include Jev `max_tokens_exceeded` if the script reports it).
- For the emitted `run_id`, every path exists:

```bash
cd /workspace/experiments/safety_decision_models_2026_10_19 && RUN_ID="<from manifest or stdout>" && \
for arm in jev clef clef-flash guardrails; do \
  for ds in toxigen openai_moderation toxicchat prompt_injections wildguardmix do_not_answer xstest harmbench jailbreakbench go_emotions emotion; do \
    test -s "outputs/predictions/${RUN_ID}/${arm}/${ds}.parquet" && test -s "outputs/predictions/${RUN_ID}/${arm}/${ds}.jsonl" || { echo "missing ${arm}/${ds}"; exit 1; }; \
  done; \
done && echo all_partitions_ok
```

Expected output: `all_partitions_ok`

Optional spot check (Clef truncation must not be silent):

```bash
cd /workspace/experiments/safety_decision_models_2026_10_19 && uv run python -c "
import pandas as pd, sys
run_id = sys.argv[1]
for arm in ('clef', 'clef-flash'):
    df = pd.read_parquet(f'outputs/predictions/{run_id}/{arm}/harmbench.parquet')
    limit = 64000 if arm == 'clef' else 24576
    over = df[df['billed_units'].fillna(0) > limit]
    bad = over[over['error_status'].isna() | (over['error_status'] == '')]
    assert len(bad) == 0, (arm, len(bad))
print('truncation_ok')
" "<RUN_ID>"
```

Expected: `truncation_ok` (or zero rows over limit on that dataset).

## Smoke check

Do **not** use the 20-item smoke from step 3 as the gate for this step. Step 3 already passed; assume cache behavior and non-empty probability or band were verified there.

This step **fails** if:

- Any expected `outputs/predictions/{run_id}/{arm}/{dataset}.parquet` or `.jsonl` is missing or empty after `--arm all`.
- Any Clef or Clef-flash row over the hosted token limit has an empty or null `error_status` (must be `truncated`).

This step does **not** require re-running `scripts/smoke.py` before the full pack.

## Cost and credentials

**Region:** `us-east-2` for Secrets Manager, Bedrock `ApplyGuardrail`, and lab AWS keys.

**Credentials (never commit):**

| Secret / env | Use |
| --- | --- |
| `jev-typesafe-api-key` (JSON `TYPESAFE_API_KEY`) | Jev via `load_typesafe_api_key` |
| `cloudflare-workers-ai` (JSON `account_id`, `api_token`) | Clef and Clef-flash |
| `hf-token` | Gated datasets (`wildguardmix`, `xstest`, and any loader that requires the form) |
| `LAB_AWS_ACCESS_KEY_ID`, `LAB_AWS_ACCESS_KEY_SECRET` (or standard AWS env names) | Guardrails `ApplyGuardrail` and guardrail version from step 5 |

Read ApplyGuardrail quota before the paid run and record it in the manifest (proposal section 4).

**Cost (proposal section 10, planning budget under US$50 for required arms; not a quote):**

| Arm | Published unit price | Estimate at ~12.9M input tokens (~20,500 requests at ~630 tokens each) |
| --- | --- | --- |
| Jev `jev-1.13.0` | US$0.042 per million input tokens | about US$0.54 |
| Clef | US$0.240 per million input tokens | about US$3.10 |
| Clef-flash | US$0.038 per million input tokens | about US$0.49 |
| Guardrails content filters | US$0.15 per 1,000 text units | about US$3.10 if each prompt is one text unit |

If jailbreak prompts average near 2,000 tokens, token volume is about three times larger (proposal table column for longer prompts). Three decision models plus one guardrail pass on short prompts is on the order of US$8; long prompts on the order of US$15 to US$30. Three separate strength calls (fallback only) can push the upper end toward US$50. The cache ensures a retry does not pay twice for the same cache key.

At ~1,100 requests per minute (Deußer et al. cap), ~21,000 requests are on the order of 20 minutes of API time before retries.

## Done when

1. Step 3 smoke and step 5 guardrail plus crosswalk are already satisfied; this run did not edit templates or the crosswalk.
2. `uv run python scripts/run_score.py --arm all` completed for arms `jev`, `clef`, `clef-flash`, and `guardrails` only.
3. For one `run_id` with the correct hash inputs, all 44 prediction partitions exist (11 datasets times 4 arms), each with matching `.parquet` and `.jsonl` row counts.
4. `cache/responses.db` contains entries for this run; cache hits on re-run do not add duplicate provider calls for the same key.
5. Clef and Clef-flash over-limit rows have `error_status` `truncated`; Jev overflow rows have `max_tokens_exceeded` where applicable; Guardrails rows have `band` set and `probability` null.
6. Truncated row count was printed; no Do-Not-Answer question text was written to any git-tracked file.
7. Manifest for `run_id` records dataset revisions, template versions, arms, prices, region, and guardrail version id.
8. No S3 upload in this step (step 7 uploads under `s3://mind-technology-lab-experiments/experiments/safety_decision_models_2026_10_19/` with the same relative paths, skipping Do-Not-Answer text).
