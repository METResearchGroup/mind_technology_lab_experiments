# Step 6: Write the comparison and upload to S3

Fill the root RESULTS file with one row per batch size plus a PR 20 reference row, draw the comparison plot, and upload the folder to S3.

## Files to inspect

- `/workspace/experiments/moral_outrage_classification_2026_09_19/RESULTS.md` (root RESULTS layout)
- `/workspace/experiments/moral_outrage_classification_2026_09_19/scripts/upload_s3.py`
- `/workspace/experiments/speedup_jev_2026_09_23/outputs/batch_*/results.json` (from step 5)

## Files allowed to change

- `/workspace/experiments/speedup_jev_2026_09_23/scripts/write_results.py`
- `/workspace/experiments/speedup_jev_2026_09_23/scripts/upload_s3.py`
- `/workspace/experiments/speedup_jev_2026_09_23/shared/metrics.py`, only to add `agreement_rate` and `mean_absolute_difference`
- `/workspace/experiments/speedup_jev_2026_09_23/RESULTS.md`, `README.md`
- `/workspace/experiments/speedup_jev_2026_09_23/outputs/comparison/`

## Files forbidden to change

- `outputs/batch_*/` (rerun step 5 instead), `models/`, and the plan files

## Details

1. `shared/metrics.py` gains `agreement_rate(a: list[int], b: list[int]) -> float` and `mean_absolute_difference(a: list[float], b: list[float]) -> float`. Both raise `ValueError` on length mismatch.
2. `scripts/write_results.py` reads every `outputs/batch_*/results.json` and `labels.parquet`, plus `data/pr20_jev_labels.parquet` and `data/pr20_jev_results.json`.
3. Drift is computed on the posts scored in both runs, joined on `source_row_id`. Each batch size is compared with today's batch size 1. The PR 20 row is also compared with today's batch size 1.
4. The PR 20 reference row takes F1, accuracy, precision, recall, and latency percentiles from `pr20_jev_results.json`. Its cost is the sum of its input tokens priced with `estimate_jev_cost_usd`. Its per-post latency equals its request latency, and its wall time is "not recorded".
5. The root `RESULTS.md` holds four tables with one row per batch size and the PR 20 row last:
   - Quality: F1, accuracy, precision, recall, scored, deadletter.
   - Latency: request p50, p90, p99, per-post p50, wall time in seconds.
   - Cost: requests, input tokens, output tokens, estimated USD, USD per 1,000 posts.
   - Drift from batch size 1: label agreement and mean absolute probability difference.
   It also states the model versions seen, the price source and date, and links the plot and each per-batch RESULTS file.
6. `outputs/comparison/f1_and_latency_by_batch_size.png` plots F1 on the left axis and p50 per-post latency on the right axis against batch size.
7. `scripts/upload_s3.py` is the PR 20 script with `PREFIX = "experiments/speedup_jev_2026_09_23/"`. It skips `.venv`, `__pycache__`, and `.env`.

## Must pass

```bash
cd /workspace/experiments/speedup_jev_2026_09_23 && uv run python scripts/write_results.py && grep -c "^| " RESULTS.md
```

Expected: the script exits 0 and the count is at least 32 (four tables, each with a header row, a separator row, and seven data rows).

```bash
cd /workspace/experiments/speedup_jev_2026_09_23 && test -s outputs/comparison/f1_and_latency_by_batch_size.png && echo ok
```

Expected output: `ok`

```bash
cd /workspace/experiments/speedup_jev_2026_09_23 && uv run python scripts/upload_s3.py && aws s3 ls s3://mind-technology-lab-experiments/experiments/speedup_jev_2026_09_23/outputs/batch_40/ --region us-east-2
```

Expected: `UPLOAD COMPLETE s3://mind-technology-lab-experiments/experiments/speedup_jev_2026_09_23/`, then a listing that includes `labels.parquet`, `requests.parquet`, `results.json`, and `RESULTS.md`. If the `aws` CLI is not installed, list the prefix with boto3 instead.

```bash
cd /workspace && uv run --extra test ruff check . && uv run --extra test ruff format --check . && uv run --extra test pyright
```

Expected: all three pass.

## Must fail

```bash
cd /workspace/experiments/speedup_jev_2026_09_23 && uv run python -c "from shared.metrics import agreement_rate; agreement_rate([1], [1, 0])"
```

Expected: exits non-zero with `ValueError`.
