# Step 1: Scaffold experiment folder, loaders, and shared scorer

## Scope

- **Caller:** Later scripts under `experiments/safety_decision_models_2026_10_19/scripts/` (`run_score.py` in steps 3, 4, and 6; `smoke.py` in step 3; `run_metrics.py` and `upload_s3.py` in step 7). Dataset loaders and scorers are imported by those runners.
- **Task:** Create the standalone experiment tree, eleven Hugging Face dataset loaders, `DecisionScorer` implementations for arms `jev`, `clef`, `clef-flash`, and `guardrails`, shared record and cache types, stub policy package, committed `configs/study.json`, docs, `.gitignore`, local `pyproject.toml`, and root ruff/pyright excludes. Implement `scripts/run_score.py` as the scoring entry point. Create stub scripts for smoke, metrics, and S3 upload.
- **Out of scope:** Question templates (`data/templates/`, step 2). Live smoke or harness runs (step 3 and 4). Creating the numbered Bedrock guardrail resource (step 5). Union, intersection, and cascade policy logic (`policies/union.py`, `intersection.py`, `cascade.py`, step 7). Metrics and threshold fitting (`shared/metrics.py`, `shared/thresholds.py`, step 7). Filling `scripts/smoke.py` beyond its stub (step 3) or `scripts/run_metrics.py` and `scripts/upload_s3.py` beyond their stubs (step 7). Paid scorer API calls in this step. A `tests/` directory, pytest, unit tests, or any `test_*.py` file. Do-Not-Answer question text in any committed file or upload.

## Files to inspect

- `/workspace/docs/plans/2026-10-19_safety-decision-model-benchmark_a7c3e1/proposal.md` (sections 4 and 5, Decisions made, Review points)
- `/workspace/docs/plans/2026-10-19_safety-decision-model-benchmark_a7c3e1/plan.md` (Step 1, inputs table, secrets list)
- `/workspace/AGENTS.md` (S3 bucket `mind-technology-lab-experiments`, lab AWS key names, standalone experiments vs `autoresearch/*`)
- `/workspace/SETUP.md` (standalone install, root uv workspace members)
- `/workspace/pyproject.toml` (`[tool.uv.workspace]`, `[tool.ruff] extend-exclude`, `[tool.pyright] exclude`)
- `/workspace/experiments/moral_outrage_classification_2026_09_19/` (standalone `pyproject.toml`, `shared/records.py` pattern, `scripts/upload_s3.py`)
- `/workspace/experiments/speedup_jev_2026_09_23/.gitignore` (base for this study's `.gitignore`)
- `/workspace/experiments/speedup_jev_2026_09_23/shared/secrets.py` (`load_typesafe_api_key`, AWS key resolution)
- `/workspace/experiments/moral_outrage_classification_2026_09_19/shared/engine_loop.py` (retry pattern for later steps)
- Public harness (not vendored): https://github.com/AppliedMachineLearning-Lab/jev-benchmarking (`jev_benchmarking/tasks/base.py`, `safety.py`, `classification.py`, `cache.py`)

## Files allowed to change

- `experiments/safety_decision_models_2026_10_19/README.md` (create)
- `experiments/safety_decision_models_2026_10_19/SETUP.md` (create)
- `experiments/safety_decision_models_2026_10_19/RESULTS.md` (create stub)
- `experiments/safety_decision_models_2026_10_19/pyproject.toml` (create, standalone; no pytest dependency)
- `experiments/safety_decision_models_2026_10_19/uv.lock` (create via `uv sync` in the experiment folder)
- `experiments/safety_decision_models_2026_10_19/.gitignore` (create)
- `experiments/safety_decision_models_2026_10_19/configs/study.json` (create)
- `experiments/safety_decision_models_2026_10_19/datasets/*.py` (create all eleven modules listed in Work)
- `experiments/safety_decision_models_2026_10_19/scorers/jev.py`, `scorers/clef.py`, `scorers/guardrails.py` (create)
- `experiments/safety_decision_models_2026_10_19/policies/__init__.py` (create empty package marker only)
- `experiments/safety_decision_models_2026_10_19/shared/records.py`, `shared/cache.py` (create)
- `experiments/safety_decision_models_2026_10_19/shared/metrics.py`, `shared/thresholds.py` (create empty modules)
- `experiments/safety_decision_models_2026_10_19/shared/__init__.py` (create if needed for imports)
- `experiments/safety_decision_models_2026_10_19/scripts/run_score.py` (create runner)
- `experiments/safety_decision_models_2026_10_19/scripts/smoke.py`, `scripts/run_metrics.py`, `scripts/upload_s3.py` (create stubs only)
- `experiments/safety_decision_models_2026_10_19/data/templates/.gitkeep`, `data/records/.gitkeep`, `data/snapshots/.gitkeep`, `cache/.gitkeep`, `outputs/.gitkeep` (create as needed)
- `/workspace/pyproject.toml` (append `experiments/safety_decision_models_2026_10_19` to ruff `extend-exclude` and pyright `exclude` only)

## Files forbidden to change

- `/workspace/pyproject.toml` `[tool.uv.workspace] members` (must stay `["autoresearch/*"]`)
- `/workspace/uv.lock`
- `/workspace/.github/workflows/ci.yml`
- `/workspace/AGENTS.md`, `/workspace/SETUP.md`, `/workspace/README.md`
- Any file under `autoresearch/`, `mech_interp_reddit/`, `openai_rate_limit_scaling/`, `ai_agent_simulation_networks/`
- `experiments/safety_decision_models_2026_10_19/policies/union.py`, `intersection.py`, `cascade.py` (step 7)
- `experiments/safety_decision_models_2026_10_19/data/templates/{dataset}.json` (step 2)
- `experiments/safety_decision_models_2026_10_19/tests/` or any `test_*.py` anywhere under the experiment folder
- Committed files that contain Do-Not-Answer question text

## Work

1. Create the folder `experiments/safety_decision_models_2026_10_19/` and the approved tree from proposal section 5. Arms in this study are only `jev`, `clef`, `clef-flash`, and `guardrails`.

```text
experiments/safety_decision_models_2026_10_19/
  README.md
  SETUP.md
  RESULTS.md
  pyproject.toml
  uv.lock
  .gitignore
  configs/study.json
  datasets/
    toxigen.py
    openai_moderation.py
    toxicchat.py
    prompt_injections.py
    wildguardmix.py
    do_not_answer.py
    xstest.py
    harmbench.py
    jailbreakbench.py
    go_emotions.py
    emotion.py
  scorers/
    jev.py
    clef.py
    guardrails.py
  policies/
    __init__.py
  shared/
    records.py
    cache.py
    metrics.py
    thresholds.py
  data/
    templates/
    records/
    snapshots/
  cache/
  scripts/
    run_score.py
    smoke.py
    run_metrics.py
    upload_s3.py
  outputs/
```

2. `pyproject.toml`: standalone project (for example package name `safety-decision-models`), `requires-python = ">=3.10"`, `[tool.uv] package = false`. Declare runtime deps needed for loaders and scorers (for example `pydantic`, `datasets`, `huggingface-hub`, `pandas`, `pyarrow`, `boto3`, `requests`, `typesafe-sdk`, `tqdm`). Do not add pytest or a `tests` extra.

3. `README.md`: link `SETUP.md` and `RESULTS.md`, state the four arms and eleven datasets, and point to the proposal plan path under `docs/plans/2026-10-19_safety-decision-model-benchmark_a7c3e1/`.

4. `SETUP.md`: region `us-east-2`, secret names and JSON fields from Cost and credentials below, output prefix `s3://mind-technology-lab-experiments/experiments/safety_decision_models_2026_10_19/`, install via `cd experiments/safety_decision_models_2026_10_19 && uv sync`. State that Do-Not-Answer question text never lands in git or S3.

5. `RESULTS.md`: stub heading plus one sentence that harness and smoke numbers are empty until later steps.

6. `configs/study.json` (committed, no secrets, no question text): pin `jev-1.13.0`, Clef and Clef-flash hosted model ids, Hugging Face repo `Cloudflare/clef` for Clef weights reference, region `us-east-2`, and unit prices as of 2026-10-19 from proposal section 10: Jev US$0.042 per million input tokens, Clef US$0.240 per million input tokens, Clef-flash US$0.038 per million input tokens, Guardrails US$0.15 per 1,000 text units on `ApplyGuardrail`. List the four arm names. Leave dataset revision fields empty until first load writes them into `outputs/manifests/{run_id}.json`.

7. `.gitignore`: copy from `experiments/speedup_jev_2026_09_23/.gitignore`, then also ignore `cache/`, `data/records/`, `data/snapshots/`, and under `outputs/` the prediction parquet/jsonl paths, metrics json, and manifests json. Do not ignore `data/templates/`, `outputs/figures/`, `RESULTS.md`, `README.md`, or `SETUP.md`.

8. `shared/records.py`: pydantic models and `DecisionScorer` protocol per Interfaces below.

9. `shared/cache.py`: SQLite response cache; cache key is a hash of arm, model version, template version, and `example_id` (same role as `request_key` in `jev_benchmarking/cache.py`).

10. `shared/metrics.py` and `shared/thresholds.py`: create files with a module docstring only. No metric or threshold logic.

11. `policies/__init__.py` only. Do not add `union.py`, `intersection.py`, or `cascade.py`.

12. Implement each dataset loader to emit `ExampleRecord` rows and, on first successful `load_dataset`, record the Hugging Face commit in the run manifest logic (local manifest helper or write path under `outputs/manifests/`). Refuse a later load when the requested revision differs from the pinned commit. Gated datasets read secret `hf-token` from AWS Secrets Manager in `us-east-2` (same pattern as other experiments; do not use `lib/load_env_vars.py` for HF).

    - `datasets/toxigen.py`: `toxigen/toxigen-data`, config `annotated`, test split per proposal.
    - `datasets/openai_moderation.py`: `mmathys/openai-moderation-api-evaluation`, default config.
    - `datasets/toxicchat.py`: `lmsys/toxic-chat`, config `toxicchat0124`.
    - `datasets/prompt_injections.py`: `deepset/prompt-injections`, default config.
    - `datasets/wildguardmix.py`: `allenai/wildguardmix`, WildGuardTest split.
    - `datasets/do_not_answer.py`: `LibrAI/do-not-answer`. Keep `risk_area` and type of harm in `metadata`. Question text may load into gitignored `data/snapshots/` or `data/records/` only, never a committed path.
    - `datasets/xstest.py`: `allenai/xstest-response`, one row per prompt, drop duplicate prompts, ignore reply labels, keep `prompt_type` in `metadata`.
    - `datasets/harmbench.py`: `swiss-ai/harmbench`, configs `DirectRequest` and `HumanJailbreaks`.
    - `datasets/jailbreakbench.py`: `JailbreakBench/JBB-Behaviors`, config `behaviors`, load `harmful` and `benign` splits; `is_benign_known` true on benign.
    - `datasets/go_emotions.py`: `google-research-datasets/go_emotions`, config `simplified`.
    - `datasets/emotion.py`: `dair-ai/emotion`, config `split`.

13. `scorers/jev.py`: implement `DecisionScorer` for arm `jev`, model version `jev-1.13.0`. Record HTTP 400 `max_tokens_exceeded` in `error_status` when the provider returns context overflow (harness behavior). Do not call the live API in this step's verification commands.

14. `scorers/clef.py`: implement `DecisionScorer` for arms `clef` and `clef-flash`. Request body fields: `model` (`clef` or `clef-flash`), `state` (text), `questions` as an object keyed by question id; each value has `type`, `instructions`, `criteria`. Read answer from `result.answers.<id>`. Billed input tokens from `result.usage.input_tokens`. If token count exceeds 64000 for `clef` or 24576 for `clef-flash`, set `error_status` to `truncated` (Workers AI may shorten `state` and still return an answer).

15. `scorers/guardrails.py`: implement `DecisionScorer` for arm `guardrails` with one detect-only `ApplyGuardrail` call, filter action `NONE`, region `us-east-2`. Do not create the numbered guardrail resource in AWS in this step (step 5). Code may accept a guardrail id from config or environment for later runs.

16. `scripts/run_score.py`: CLI that loads records for a dataset, loads the template `QuestionSpec` from `data/templates/{dataset}.json` when present (step 2), runs the chosen scorer, writes through `shared/cache.py`, and is the entry steps 3, 4, and 6 will call. Stub or no-op paid calls until templates exist.

17. `scripts/smoke.py`, `scripts/run_metrics.py`, `scripts/upload_s3.py`: create files with `main` guard and docstring stating `smoke.py` is filled in step 3 and `run_metrics.py` and `upload_s3.py` in step 7. No full smoke, metrics, or upload logic yet.

18. In `/workspace/pyproject.toml`, add `"experiments/safety_decision_models_2026_10_19"` to `tool.ruff.extend-exclude` and `tool.pyright.exclude`, matching the `experiments/moral_outrage_classification_2026_09_19` entries.

## Interfaces

Define these in `experiments/safety_decision_models_2026_10_19/shared/records.py` (field names must match the proposal).

**ExampleRecord**

| Field | Type | Notes |
| --- | --- | --- |
| `example_id` | `str` | Stable id per row |
| `dataset` | `str` | Short dataset name |
| `split` | `str` | Hugging Face split name |
| `text` | `str` | Prompt or user text scored |
| `gold_labels` | `dict[str, bool] \| str` | Binary harm bit, multi-label map, or class name |
| `harm_category` | `str \| None` | Dataset-specific harm label when present |
| `is_benign_known` | `bool` | True only when the dataset marks the row benign |
| `metadata` | `dict[str, str \| bool]` | Adversarial flag, `prompt_type`, risk area, type of harm, etc. |

**QuestionSpec**

JSON matching the public harness `choice`, `noul`, and `score` builders in `jev_benchmarking/tasks/base.py` (Choice, Noul, or Score). Loaded from `data/templates/{dataset}.json` in later steps; types only in this step.

**DecisionScorer**

```python
class DecisionScorer(Protocol):
    def score(
        self, records: list[ExampleRecord], question: QuestionSpec
    ) -> list[PredictionRecord]: ...
```

**PredictionRecord**

| Field | Type | Notes |
| --- | --- | --- |
| `example_id` | `str` | Matches example row |
| `arm` | `str` | `jev`, `clef`, `clef-flash`, or `guardrails` |
| `model_version` | `str` | Pin string (for example `jev-1.13.0`) |
| `template_version` | `str` | Hash of template JSON |
| `probability` | `float \| None` | Noul or Choice top option; null for guardrail-only rows |
| `band` | `str \| None` | Guardrails band `NONE`, `LOW`, `MEDIUM`, `HIGH` |
| `raw_response` | `dict` | Provider JSON |
| `latency_ms` | `float` | Client wall time |
| `billed_units` | `float` | Tokens or text units |
| `error_status` | `str \| None` | For example `truncated`, `max_tokens_exceeded`, or provider error code |

**Cache key**

Hash of arm, model version, template version, and `example_id`. A cache hit must not call the provider again.

**Clef request shape** (in `scorers/clef.py`)

```python
{
    "model": "clef",  # or "clef-flash"
    "state": text,
    "questions": {
        "<question_id>": {
            "type": "noul",  # or choice, score
            "instructions": "...",
            "criteria": None,
        },
    },
}
```

Answer: `result.answers["<question_id>"]`. Billed tokens: `result.usage.input_tokens`.

## Commands

```bash
cd experiments/safety_decision_models_2026_10_19 && uv sync
```

Expected: exit code 0. A `.venv` (or uv project environment) exists under the experiment folder. `/workspace/uv.lock` is unchanged.

```bash
test ! -d experiments/safety_decision_models_2026_10_19/tests
```

Expected: exit code 0 (no `tests/` directory).

```bash
grep -n 'members = \["autoresearch/\*"\]' /workspace/pyproject.toml
```

Expected: prints the workspace members line showing only `autoresearch/*`.

```bash
test -f experiments/safety_decision_models_2026_10_19/shared/records.py
test -f experiments/safety_decision_models_2026_10_19/shared/cache.py
test -f experiments/safety_decision_models_2026_10_19/scorers/jev.py
test -f experiments/safety_decision_models_2026_10_19/scorers/clef.py
test -f experiments/safety_decision_models_2026_10_19/scorers/guardrails.py
test -f experiments/safety_decision_models_2026_10_19/scripts/run_score.py
test -f experiments/safety_decision_models_2026_10_19/configs/study.json
test -f experiments/safety_decision_models_2026_10_19/policies/__init__.py
test ! -f experiments/safety_decision_models_2026_10_19/policies/union.py
```

Expected: all `test` and `test !` commands exit 0.

```bash
grep -n 'safety_decision_models_2026_10_19' /workspace/pyproject.toml
```

Expected: at least one line under ruff `extend-exclude` and one under pyright `exclude`.

```bash
grep -rn 'do-not-answer\|do_not_answer' experiments/safety_decision_models_2026_10_19/data/templates 2>/dev/null || true
find experiments/safety_decision_models_2026_10_19 -name 'test_*.py' | wc -l
```

Expected: no template files with question text in step 1. `wc -l` prints `0`.

Optional local dataset pin check (uses `hf-token` when the dataset is gated; no scorer calls):

```bash
cd experiments/safety_decision_models_2026_10_19 && uv run python -c "from datasets import toxigen; print(len(toxigen.load_records('test')[:1]))"
```

Expected: prints `1` when credentials and network allow. First successful load records the Hugging Face commit for that dataset in manifest state; a second load with a different revision must raise or exit with a clear refusal.

## Smoke check

Not run in this step. `scripts/smoke.py` is a stub here. Step 3 fills and runs the 20-item smoke test per arm (`jev`, `clef`, `clef-flash`, `guardrails`). This step passes on file existence, root excludes, no `tests/` directory, and `uv sync` in the experiment folder.

## Cost and credentials

Region for secrets and Bedrock calls: `us-east-2`.

Secrets (AWS Secrets Manager or environment, never committed):

| Secret | Field or use |
| --- | --- |
| `jev-typesafe-api-key` | JSON `TYPESAFE_API_KEY` |
| `hf-token` | Hugging Face token for gated datasets |
| `cloudflare-workers-ai` | JSON `account_id`, `api_token` |
| Lab AWS | `LAB_AWS_ACCESS_KEY_ID`, `LAB_AWS_ACCESS_KEY_SECRET` (Bedrock and Secrets Manager) |

This step may download public or gated datasets from Hugging Face when verifying loaders. Do not run paid Jev, Clef, Clef-flash, or Guardrails scoring in this step. Model spend for this step is zero.

## Done when

1. `experiments/safety_decision_models_2026_10_19/` exists with the tree above, standalone `pyproject.toml`, and no `tests/` directory.
2. All eleven dataset modules exist and implement pin-on-first-load plus revision refusal on mismatch.
3. `shared/records.py` and `shared/cache.py` implement the interfaces above; `shared/metrics.py` and `shared/thresholds.py` are empty stubs.
4. `scorers/jev.py`, `scorers/clef.py`, and `scorers/guardrails.py` implement `DecisionScorer` for the four arms (Clef and Clef-flash share `clef.py`).
5. `policies/` contains only `__init__.py`.
6. `scripts/run_score.py` exists; `smoke.py`, `run_metrics.py`, and `upload_s3.py` are stubs for later steps.
7. `configs/study.json` is committed with pins, 2026-10-19 prices, and `us-east-2`, with no secrets and no question text.
8. `.gitignore` follows the speedup base plus `cache/`, `data/records/`, `data/snapshots/`, and the listed `outputs/` artifacts; templates and figures remain tracked.
9. Root `pyproject.toml` excludes the experiment from ruff and pyright and keeps `[tool.uv.workspace] members = ["autoresearch/*"]`.
10. Do-Not-Answer question text appears in no committed file.

Ready for Step 2 to add confirmed templates under `data/templates/`.
