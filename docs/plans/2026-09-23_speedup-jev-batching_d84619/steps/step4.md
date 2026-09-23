# Step 4: Run the smoke test

Score the first 40 sample posts at batch sizes 5 and 40 with the live engine from step 3, and stop if any post has no answer.

## Files to inspect

- `/workspace/experiments/speedup_jev_2026_09_23/shared/batch_runner.py`
- `/workspace/experiments/speedup_jev_2026_09_23/models/batched_jev.py`

## Files allowed to change

- `/workspace/experiments/speedup_jev_2026_09_23/scripts/smoke.py`
- `/workspace/experiments/speedup_jev_2026_09_23/SETUP.md`, only to add the smoke command

## Files forbidden to change

- `shared/`, `models/`, and the plan files. If the smoke test shows a bug there, stop and report it.

## Details

1. `scripts/smoke.py` takes no arguments. It loads the sample, keeps the first 40 posts by `int(source_row_id)`, and deletes any earlier `outputs/smoke/batch_5/` and `outputs/smoke/batch_40/` so the smoke test always sends requests.
2. For each of batch sizes 5 and 40 it calls `run_pass` with output folder `outputs/smoke/batch_{n}/`.
3. It prints one row per batch size with these columns: `batch_size`, `answered`, `deadletter`, `requests`, `p50_request_ms`, `input_tokens`, `estimated_cost_usd`.
4. It exits with code 1 when any batch size has fewer than 40 answered posts.

## Must pass

```bash
cd /workspace/experiments/speedup_jev_2026_09_23 && uv run python scripts/smoke.py
```

Expected: two table rows, `answered` is 40 and `deadletter` is 0 in both, `requests` is 8 for batch size 5 and 1 for batch size 40, and exit code 0.

## Must fail

No extra command. A deadletter or missing answer makes the smoke command above exit 1, which blocks step 5.
