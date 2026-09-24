# Step 4: Write ablation RESULTS, upload, and update CHANGELOG

Aggregate the five passes into `ablation_full_dataset/RESULTS.md`, compare against the main 1,000-post run on overlapping posts, upload to S3, and record the ablation in CHANGELOG.

## Files to inspect

- `/workspace/experiments/speedup_jev_2026_09_23/scripts/write_results.py` (main comparison layout)
- `/workspace/experiments/speedup_jev_2026_09_23/RESULTS.md` (main-run F1 values for same-posts table)
- `/workspace/experiments/speedup_jev_2026_09_23/shared/data.py` (`load_sample` for 1,000 id list)
- `/workspace/experiments/speedup_jev_2026_09_23/scripts/upload_s3.py`
- `/workspace/CHANGELOG.md`

## Files allowed to change

- `/workspace/experiments/speedup_jev_2026_09_23/ablation_full_dataset/scripts/write_results.py`
- `/workspace/experiments/speedup_jev_2026_09_23/ablation_full_dataset/RESULTS.md`
- `/workspace/experiments/speedup_jev_2026_09_23/ablation_full_dataset/outputs/comparison/`
- `/workspace/experiments/speedup_jev_2026_09_23/ablation_full_dataset/README.md`
- `/workspace/CHANGELOG.md`

## Files forbidden to change

- Main-run `RESULTS.md` and `outputs/batch_*` (except verifying unchanged)
- The plan files under `/workspace/docs/plans/2026-09-23_speedup-jev-full-dataset-ablation_8c7ae1/`

## Contracts

`ablation_full_dataset/scripts/write_results.py` reads:

- `ablation_full_dataset/outputs/batch_{10,20,40,60,80}/results.json` and `labels.parquet`
- Main sample ids via `load_sample()` from parent `shared/data.py`
- Main-run labels from `outputs/batch_{10,20,40}/labels.parquet` for same-posts comparison

Constants:

- `MAIN_REFERENCE_F1_BATCH1 = 0.752` (1,000-post sample, batch size 1; label clearly in table header)
- `FULL_DATA_BASELINE_BATCH_SIZE = 10` (drift reference on full 26k)
- `PROJECTION_REQUESTS_PER_MIN = 1000`
- `PROJECTION_POSTS_20M = 20_000_000`

Derived fields per batch size row:

- `sustained_posts_per_min = n_scored / wall_time_seconds * 60`
- `projected_posts_per_min = PROJECTION_REQUESTS_PER_MIN * batch_size`
- `projected_cost_20m_usd = (estimated_cost_usd / n_scored) * PROJECTION_POSTS_20M`
- `projected_wall_hours_20m = (PROJECTION_POSTS_20M / batch_size) / PROJECTION_REQUESTS_PER_MIN / 60`
- `share_of_reference_f1 = f1 / MAIN_REFERENCE_F1_BATCH1` (full-data F1 over sample batch-1 F1)

Same-posts table (batch sizes 10, 20, 40 only):

- Join ablation and main labels on `source_row_id` for the 1,000 sample ids.
- Columns: batch size, ablation F1 on sample, main-run F1 on sample, label agreement, share of reference F1.

`ablation_full_dataset/RESULTS.md` sections:

1. Quality table
2. Latency table (include sustained and projected posts per minute columns)
3. Cost table (include USD per 1,000 posts and 20M projection columns)
4. Drift from batch size 10 on full data
5. Same-posts comparison (10, 20, 40)
6. Notes: separate ablation, no full-data batch size 1, shuffle seed `20260923`, model `jev-1.13.0`, reference F1 0.752 is from 1,000-post sample
7. Link plot `ablation_full_dataset/outputs/comparison/f1_and_latency_by_batch_size.png`

Plot: F1 (left axis) and per-post p50 latency (right axis) vs batch size for 10, 20, 40, 60, 80.

Upload:

```bash
cd /workspace/experiments/speedup_jev_2026_09_23 && uv run python scripts/upload_s3.py
```

Expect prefix listing to include `ablation_full_dataset/outputs/batch_80/results.json`.

CHANGELOG entry under latest date:

- One bullet summarizing the ablation folder, batch sizes, shuffle seed, and estimated spend.
- PR section heading exactly: `Ablation: full 26k dataset (separate from the main experiment)`

## Must pass

```bash
cd /workspace/experiments/speedup_jev_2026_09_23 && uv run python ablation_full_dataset/scripts/write_results.py && grep -c "^| " ablation_full_dataset/RESULTS.md
```

Expected: exit 0 and count at least 40 (five tables with headers, separators, and five data rows each, plus same-posts rows).

```bash
cd /workspace/experiments/speedup_jev_2026_09_23 && test -s ablation_full_dataset/outputs/comparison/f1_and_latency_by_batch_size.png && echo ok
```

Expected output: `ok`

```bash
cd /workspace/experiments/speedup_jev_2026_09_23 && uv run python ablation_full_dataset/scripts/write_results.py && grep -F "0.752" ablation_full_dataset/RESULTS.md | head -1
```

Expected: a line mentioning 0.752 as the 1,000-post sample batch-1 reference, not full-data batch 1.

```bash
cd /workspace/experiments/speedup_jev_2026_09_23 && uv run python scripts/upload_s3.py 2>&1 | tail -1
```

Expected line contains `UPLOAD COMPLETE s3://mind-technology-lab-experiments/experiments/speedup_jev_2026_09_23/`

```bash
cd /workspace && uv run --extra test ruff check . && uv run --extra test ruff format --check . && uv run --extra test pyright
```

Expected: all three pass.

## Must fail

```bash
cd /workspace/experiments/speedup_jev_2026_09_23 && uv run python -c "
from shared.metrics import agreement_rate
agreement_rate([1], [1, 0])
"
```

Expected: exits non-zero with `ValueError`.

## Done when

1. `ablation_full_dataset/RESULTS.md` contains all tables, notes, and plot link from decision 6.
2. Same-posts table shows ablation vs main F1 for batch sizes 10, 20, and 40 on the 1,000 sample ids.
3. S3 upload includes the ablation prefix.
4. CHANGELOG has the ablation entry and PR section heading.
5. Root lint and CI still pass.
