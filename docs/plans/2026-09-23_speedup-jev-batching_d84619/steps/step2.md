# Step 2: Download the sample and load the key

Download the PR 20 sample, its manifest, and the PR 20 Jev labels from S3. Check the manifest against decision 3. Then make one single-post Jev request to confirm the TypeSafe key works.

## Files to inspect

- `/workspace/experiments/moral_outrage_classification_2026_09_19/shared/data.py` (sample constants and manifest keys)
- `/workspace/experiments/moral_outrage_classification_2026_09_19/models/jev.py` (the single-post request)
- `/workspace/experiments/speedup_jev_2026_09_23/shared/secrets.py` (from step 1)

## Files allowed to change

- `/workspace/experiments/speedup_jev_2026_09_23/shared/data.py`
- `/workspace/experiments/speedup_jev_2026_09_23/scripts/fetch_inputs.py`
- `/workspace/experiments/speedup_jev_2026_09_23/scripts/check_typesafe_key.py`
- `/workspace/experiments/speedup_jev_2026_09_23/README.md` and `SETUP.md`, only to fix commands that change in this step

## Files forbidden to change

- Anything under `/workspace/experiments/moral_outrage_classification_2026_09_19/`
- The plan files under `/workspace/docs/plans/2026-09-23_speedup-jev-batching_d84619/`

## Details

1. `shared/data.py` holds these constants.
   - `SOURCE_BUCKET = "mind-technology-lab-experiments"` and `SOURCE_PREFIX = "experiments/moral_outrage_classification_2026_09_19/"`.
   - Remote keys: `data/sample_1000.parquet`, `data/sample_1000.manifest.json`, `outputs/jev/labels.parquet`, and `outputs/jev/results.json`, all under `SOURCE_PREFIX`.
   - Local names under `data/`: `sample_1000.parquet`, `sample_1000.manifest.json`, `pr20_jev_labels.parquet`, and `pr20_jev_results.json`.
   - Expected manifest values: `SAMPLE_SEED = 20260919`, `SAMPLE_ROW_COUNT = 1000`, `SAMPLE_GOLD_0_COUNT = 560`, `SAMPLE_GOLD_1_COUNT = 440`, `ROW_ID_FIELD = "source_row_id"`.
2. `shared/data.py` exposes these functions.
   - `download_inputs() -> None` downloads each of the four files that is not already on disk. It uses the boto3 session from `shared/secrets.py`.
   - `validate_manifest(manifest: dict[str, object]) -> None` raises `ValueError` when the seed, row count, gold 0 count, gold 1 count, or row id field differs from the constants.
   - `load_sample() -> pd.DataFrame` reads the sample, validates the manifest and the actual gold counts of the frame, and returns the rows sorted by `int(source_row_id)`.
   - `load_pr20_jev_labels() -> pd.DataFrame` reads `data/pr20_jev_labels.parquet`.
3. `scripts/fetch_inputs.py` calls `download_inputs()`, then `load_sample()`, then `load_pr20_jev_labels()`, and prints `sample rows=1000 gold_0=560 gold_1=440 seed=20260919` and `pr20 jev rows=1000`.
4. `scripts/check_typesafe_key.py` sends one request with the first sample post as the state and one Noul question with id `moral_outrage` and the PR 20 instructions, on model `jev-1.13.0`. It prints `ok model=<response model> noul=<value rounded to 4 places> input_tokens=<n>`. It never prints the key.

## Must pass

```bash
cd /workspace/experiments/speedup_jev_2026_09_23 && uv run python scripts/fetch_inputs.py
```

Expected output:

```text
sample rows=1000 gold_0=560 gold_1=440 seed=20260919
pr20 jev rows=1000
```

```bash
cd /workspace/experiments/speedup_jev_2026_09_23 && uv run python scripts/check_typesafe_key.py
```

Expected: one line starting with `ok model=jev-1.13.0 noul=`, and exit code 0.

```bash
cd /workspace/experiments/speedup_jev_2026_09_23 && git status --porcelain data/
```

Expected: no output, because the downloaded parquet and json files are gitignored.

## Must fail

```bash
cd /workspace/experiments/speedup_jev_2026_09_23 && uv run python -c "from shared.data import validate_manifest; validate_manifest({'seed': 1, 'n_rows': 1000, 'n_gold_0': 560, 'n_gold_1': 440, 'row_id_field': 'source_row_id'})"
```

Expected: exits non-zero with a `ValueError` that names the seed.
