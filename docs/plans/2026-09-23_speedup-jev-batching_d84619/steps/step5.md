# Step 5: Run the six full passes

Run batch sizes 1, 5, 10, 20, 30, and 40 over all 1,000 posts, one pass after another. Each pass writes its own outputs.

## Files to inspect

- `/workspace/experiments/moral_outrage_classification_2026_09_19/outputs/jev/RESULTS.md` (per-model RESULTS layout)
- `/workspace/experiments/speedup_jev_2026_09_23/shared/batch_runner.py`
- `/workspace/experiments/speedup_jev_2026_09_23/shared/metrics.py`

## Files allowed to change

- `/workspace/experiments/speedup_jev_2026_09_23/scripts/run_batch_size.py`
- `/workspace/experiments/speedup_jev_2026_09_23/shared/metrics.py`, only to add summary helpers used by this script
- Everything under `/workspace/experiments/speedup_jev_2026_09_23/outputs/batch_*/`

## Files forbidden to change

- `models/`, `shared/batch_runner.py`, `shared/rate_limiter.py`, and the plan files

## Details

1. `scripts/run_batch_size.py --batch-size N` accepts only 1, 5, 10, 20, 30, or 40. It calls `run_pass` for all 1,000 sample posts with output folder `outputs/batch_{N}/`.
2. After the pass, it converts `predictions.jsonl` to `labels.parquet` and `requests.jsonl` to `requests.parquet`.
3. It writes `results.json` with these keys: `batch_size`, `n_scored`, `n_deadletter`, `n_requests`, `f1`, `accuracy`, `precision`, `recall`, `request_latency_ms` (p50, p90, p99), `per_post_latency_ms_p50`, `wall_time_seconds` (from the last line of `runs.jsonl`), `input_tokens`, `output_tokens`, `estimated_cost_usd`, `model_versions` (sorted unique list), and `price_source`.
4. It writes `static/score_hist.png`, a bar histogram of probabilities with 10 bins from 0 to 1.
5. It writes `RESULTS.md` with one table holding the `results.json` values, and a link to the histogram.
6. Run the six passes in this order: 1, 5, 10, 20, 30, 40.

## Must pass

```bash
cd /workspace/experiments/speedup_jev_2026_09_23 && for n in 1 5 10 20 30 40; do uv run python scripts/run_batch_size.py --batch-size $n || break; done
```

Expected: each pass prints a final line `batch_size=N scored=1000 deadletter=0 requests=R`, where R is 1000, 200, 100, 50, 34, and 25. If any deadletter is above 0, the line still prints and `deadletter.jsonl` lists every failed post.

```bash
cd /workspace/experiments/speedup_jev_2026_09_23 && uv run python -c "import json; [print(n, json.load(open(f'outputs/batch_{n}/results.json'))['n_scored']) for n in (1, 5, 10, 20, 30, 40)]"
```

Expected: six lines, each ending in `1000` (or 1000 minus that pass's deadletter count).

## Must fail

```bash
cd /workspace/experiments/speedup_jev_2026_09_23 && uv run python scripts/run_batch_size.py --batch-size 7
```

Expected: exits non-zero with an argparse error that lists the allowed batch sizes, and sends no request.
