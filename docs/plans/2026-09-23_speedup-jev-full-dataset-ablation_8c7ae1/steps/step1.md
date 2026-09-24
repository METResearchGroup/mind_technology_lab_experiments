# Step 1: Scaffold the ablation folder and full-dataset loader

Create the ablation subfolder, add `shared/full_dataset.py` for download and shuffle, and implement `fetch_full_dataset.py`. This step sends no Jev requests.

## Files to inspect

- `/workspace/experiments/speedup_jev_2026_09_23/README.md`
- `/workspace/experiments/speedup_jev_2026_09_23/.gitignore`
- `/workspace/experiments/speedup_jev_2026_09_23/shared/data.py` (sample loader pattern)
- `/workspace/experiments/moral_outrage_classification_2026_09_19/shared/data.py` (`load_full_frame`, `validate_full_frame`, S3 constants)
- `/workspace/experiments/speedup_jev_2026_09_23/shared/records.py` (`PostTask`)

## Files allowed to change

- Everything under `/workspace/experiments/speedup_jev_2026_09_23/ablation_full_dataset/` (new)
- `/workspace/experiments/speedup_jev_2026_09_23/shared/full_dataset.py` (new)

## Files forbidden to change

- Main-run outputs under `/workspace/experiments/speedup_jev_2026_09_23/outputs/batch_*`
- `/workspace/experiments/speedup_jev_2026_09_23/shared/batch_runner.py` (step 2)
- `/workspace/experiments/speedup_jev_2026_09_23/scripts/run_batch_size.py` (step 2)
- The plan files under `/workspace/docs/plans/2026-09-23_speedup-jev-full-dataset-ablation_8c7ae1/`

## File tree

```text
experiments/speedup_jev_2026_09_23/
  shared/
    full_dataset.py              # new in this step
  ablation_full_dataset/
    README.md
    RESULTS.md                   # stub until step 4
    data/.gitkeep
    outputs/.gitkeep
    scripts/
      fetch_full_dataset.py      # this step
      smoke.py                   # stub until step 2
      run_batch_size.py          # stub until step 2
      write_results.py           # stub until step 4
```

Add `data/*.csv` to a local `.gitignore` inside `ablation_full_dataset/` if the parent gitignore does not already cover it.

## Contracts

Constants in `shared/full_dataset.py`:

- `SOURCE_BUCKET = "met-research-group-datasets"`
- `SOURCE_KEY = "moral_outrage_classifier/26k_training_data.csv"`
- `SOURCE_URI = "s3://met-research-group-datasets/moral_outrage_classifier/26k_training_data.csv"`
- `FULL_CSV_NAME = "26k_training_data.csv"`
- `TEXT_COLUMN = "text"`
- `GOLD_COLUMN = "outrage"`
- `ROW_ID_FIELD = "source_row_id"`
- `FULL_ROW_COUNT = 26000`
- `FULL_GOLD_0_COUNT = 14563`
- `FULL_GOLD_1_COUNT = 11437`
- `SHUFFLE_SEED = 20260923`
- `ABLATION_BATCH_SIZES = (10, 20, 40, 60, 80)`
- `ABLATION_ROOT = Path(__file__).resolve().parent.parent / "ablation_full_dataset"`
- `DATA_DIR = ABLATION_ROOT / "data"`

Functions:

- `download_full_csv(destination: Path | None = None) -> Path`
- `load_full_frame(csv_path: Path) -> pd.DataFrame` (columns: `source_row_id`, `text`, `gold_label`; row ids are `str(index)`)
- `validate_full_frame(frame: pd.DataFrame) -> None`
- `shuffled_tasks(seed: int = SHUFFLE_SEED) -> list[PostTask]` (loads CSV from `DATA_DIR`, validates, shuffles with `numpy.random.default_rng(seed)`, returns tasks in shuffle order)
- `shuffled_frame(seed: int = SHUFFLE_SEED) -> pd.DataFrame` (same shuffle, returns dataframe)

`scripts/fetch_full_dataset.py` calls `download_full_csv()`, `load_full_frame()`, and prints:

```text
full rows=26000 gold_0=14563 gold_1=11437
shuffle_seed=20260923
```

## Details

1. Copy parsing logic from PR 20 `load_full_frame` and `validate_full_frame`. Do not import across experiment folders.
2. `README.md` states this is a separate ablation on 26,000 posts, lists batch sizes 10/20/40/60/80, seed `20260923`, model `jev-1.13.0`, and points to parent SETUP for install and secrets.
3. `RESULTS.md` stub says "pending run".
4. Reuse boto3 session helpers from `shared/secrets.py` and region from `shared/aws_region.py`.

## Must pass

```bash
cd /workspace/experiments/speedup_jev_2026_09_23 && uv run python ablation_full_dataset/scripts/fetch_full_dataset.py
```

Expected output:

```text
full rows=26000 gold_0=14563 gold_1=11437
shuffle_seed=20260923
```

```bash
cd /workspace/experiments/speedup_jev_2026_09_23 && uv run python -c "
from shared.full_dataset import shuffled_tasks, SHUFFLE_SEED, FULL_ROW_COUNT
tasks = shuffled_tasks()
assert len(tasks) == FULL_ROW_COUNT
ids = [t.source_row_id for t in tasks]
assert len(set(ids)) == FULL_ROW_COUNT
print('seed', SHUFFLE_SEED, 'tasks', len(tasks))
"
```

Expected output: `seed 20260923 tasks 26000`

```bash
cd /workspace/experiments/speedup_jev_2026_09_23 && git status --porcelain ablation_full_dataset/data/
```

Expected: no output (CSV is gitignored).

## Must fail

```bash
cd /workspace/experiments/speedup_jev_2026_09_23 && uv run python -c "
import pandas as pd
from pathlib import Path
from shared.full_dataset import validate_full_frame
bad = pd.DataFrame({'gold_label': [0, 1]})
validate_full_frame(bad)
"
```

Expected: exits non-zero with `ValueError` naming row count.

## Done when

1. Ablation folder tree exists with README and stub scripts.
2. Full CSV downloads and validates to 26,000 rows with the locked gold counts.
3. `shuffled_tasks()` returns 26,000 unique tasks in a reproducible order for seed `20260923`.
