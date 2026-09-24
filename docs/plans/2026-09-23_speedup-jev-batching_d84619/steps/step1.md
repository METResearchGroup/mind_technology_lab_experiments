# Step 1: Scaffold the experiment folder and documents

Create the standalone experiment folder, copy the small helpers from the PR 20 experiment, and keep the new folder out of root lint. This step writes no Jev request code.

## Files to inspect

- `/workspace/experiments/moral_outrage_classification_2026_09_19/pyproject.toml`
- `/workspace/experiments/moral_outrage_classification_2026_09_19/.gitignore`
- `/workspace/experiments/moral_outrage_classification_2026_09_19/shared/aws_region.py`
- `/workspace/experiments/moral_outrage_classification_2026_09_19/shared/secrets.py`
- `/workspace/experiments/moral_outrage_classification_2026_09_19/shared/timer.py`
- `/workspace/experiments/moral_outrage_classification_2026_09_19/shared/metrics.py`
- `/workspace/experiments/moral_outrage_classification_2026_09_19/shared/brady_definition.py`
- `/workspace/pyproject.toml` (the `[tool.ruff] extend-exclude` and `[tool.pyright] exclude` lists)

## Files allowed to change

- Everything under `/workspace/experiments/speedup_jev_2026_09_23/` (new)
- `/workspace/pyproject.toml`, only to add `experiments/speedup_jev_2026_09_23` to the two exclude lists

## Files forbidden to change

- Anything under `/workspace/experiments/moral_outrage_classification_2026_09_19/`
- `/workspace/uv.lock`, and the root uv workspace member list
- The plan files under `/workspace/docs/plans/2026-09-23_speedup-jev-batching_d84619/`

## File tree

```text
experiments/speedup_jev_2026_09_23/
  README.md
  SETUP.md
  RESULTS.md                # stub until step 6
  pyproject.toml
  uv.lock                   # from `uv sync`
  .gitignore
  data/.gitkeep
  models/__init__.py
  models/batched_jev.py     # step 3
  shared/__init__.py
  shared/aws_region.py      # copied
  shared/secrets.py         # copied, TypeSafe key only
  shared/timer.py           # copied
  shared/metrics.py         # copied, plus agreement helpers in step 6
  shared/brady_definition.py
  shared/pricing.py
  shared/records.py         # step 3
  shared/data.py            # step 2
  shared/rate_limiter.py    # step 3
  shared/batch_runner.py    # step 3
  scripts/fetch_inputs.py   # step 2
  scripts/check_typesafe_key.py  # step 2
  scripts/smoke.py          # step 4
  scripts/run_batch_size.py # step 5
  scripts/write_results.py  # step 6
  scripts/upload_s3.py      # step 6
  outputs/.gitkeep
```

Create each file that belongs to a later step as a module with only its file docstring, so later steps fill it in.

## Details

1. `pyproject.toml` declares project name `speedup-jev`, `requires-python = ">=3.10"`, `[tool.uv] package = false`, and these dependencies: `boto3>=1.35.0`, `matplotlib>=3.8.0`, `numpy>=1.24.0`, `pandas>=2.2.0`, `pyarrow>=16.0.0`, `pydantic>=2.7.0`, `typesafe-sdk>=0.7.0`.
2. `.gitignore` matches the PR 20 file: ignore `.venv/`, `data/*.parquet`, `data/*.json`, `outputs/**/*.parquet`, `outputs/**/*.json`, `outputs/**/*.jsonl`, and `__pycache__/`, and keep `data/.gitkeep` and `outputs/.gitkeep`.
3. Copy `aws_region.py`, `timer.py`, and `metrics.py` unchanged except for the file docstring and imports. In `metrics.py`, drop `paired_difference_summary` and `DIFFERENCE_KEYS`, which compared Jev with Perspective. Copy the positive threshold constant `POSITIVE_PROBABILITY_THRESHOLD = 0.5` into `metrics.py`, because the PR 20 `records.py` is not copied.
4. Copy `secrets.py`, keep only the TypeSafe loader and the AWS key resolution, and drop the Google key functions.
5. `brady_definition.py` holds two constants. `BRADY_MORAL_OUTRAGE_DEFINITION` is the PR 20 text starting at "Moral outrage means all three of the following". `BRADY_MORAL_OUTRAGE_INSTRUCTIONS` is `"Does this post express moral outrage? " + BRADY_MORAL_OUTRAGE_DEFINITION`, which must equal the PR 20 string character for character.
6. `pricing.py` holds `JEV_USD_PER_MILLION_INPUT_TOKENS = 0.042`, `JEV_USD_PER_MILLION_OUTPUT_TOKENS = 0.0`, `PRICE_PAGE_URL = "https://docs.typesafe.ai/models"`, `PRICE_PAGE_DATE = "2026-09-23"`, and `estimate_jev_cost_usd(input_tokens: int, output_tokens: int) -> float`.
7. README says what the experiment measures, links issue 17 and PR 20, and points to SETUP and RESULTS. SETUP lists the install command, the sample URI, the secret name and JSON field, the region, the pinned model `jev-1.13.0`, the batch sizes, 8 threads, the 1,000 per minute cap, the price and its source, and the output prefix.
8. Add `experiments/speedup_jev_2026_09_23` to both exclude lists in `/workspace/pyproject.toml`, next to the PR 20 entry.

## Must pass

```bash
cd /workspace/experiments/speedup_jev_2026_09_23 && uv sync
```

Expected: exits 0 and creates `.venv/`.

```bash
cd /workspace/experiments/speedup_jev_2026_09_23 && uv run python -c "from shared.brady_definition import BRADY_MORAL_OUTRAGE_INSTRUCTIONS as a; import importlib.util as u; s=u.spec_from_file_location('old','../moral_outrage_classification_2026_09_19/shared/brady_definition.py'); m=u.module_from_spec(s); s.loader.exec_module(m); print(a == m.BRADY_MORAL_OUTRAGE_INSTRUCTIONS)"
```

Expected output: `True`

```bash
cd /workspace/experiments/speedup_jev_2026_09_23 && uv run python -c "from shared.pricing import estimate_jev_cost_usd; print(round(estimate_jev_cost_usd(349632, 0), 6))"
```

Expected output: `0.014685`

```bash
cd /workspace && uv run --extra test ruff check . && uv run --extra test ruff format --check . && uv run --extra test pyright
```

Expected: all three pass, and none of them reports a file under `experiments/speedup_jev_2026_09_23/`.

## Must fail

Nothing in this step calls TypeSafe, so no command in this step needs the TypeSafe key.
