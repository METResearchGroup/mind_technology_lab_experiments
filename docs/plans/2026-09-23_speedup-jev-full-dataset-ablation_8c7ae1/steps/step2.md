# Step 2: Preserve shuffle order, wire run scripts, and smoke test

Fix batch ordering if needed, expose reusable pass post-processing from the main run script, and smoke test the first 80 shuffled posts at batch sizes 60 and 80.

## Files to inspect

- `/workspace/experiments/speedup_jev_2026_09_23/shared/batch_runner.py` (`make_batches`, `run_pass`)
- `/workspace/experiments/speedup_jev_2026_09_23/scripts/run_batch_size.py` (post-processing helpers to import)
- `/workspace/experiments/speedup_jev_2026_09_23/scripts/smoke.py` (main-run smoke pattern)
- `/workspace/experiments/speedup_jev_2026_09_23/shared/full_dataset.py` (from step 1)

## Files allowed to change

- `/workspace/experiments/speedup_jev_2026_09_23/shared/batch_runner.py` (only if order fix is needed)
- `/workspace/experiments/speedup_jev_2026_09_23/scripts/run_batch_size.py` (parameterization for import; must keep main-run byte-identical outputs)
- `/workspace/experiments/speedup_jev_2026_09_23/ablation_full_dataset/scripts/smoke.py`
- `/workspace/experiments/speedup_jev_2026_09_23/ablation_full_dataset/scripts/run_batch_size.py`
- `/workspace/experiments/speedup_jev_2026_09_23/ablation_full_dataset/README.md` (add smoke command)

## Files forbidden to change

- Main-run outputs under `/workspace/experiments/speedup_jev_2026_09_23/outputs/batch_*`
- `/workspace/experiments/speedup_jev_2026_09_23/models/batched_jev.py`
- The plan files under `/workspace/docs/plans/2026-09-23_speedup-jev-full-dataset-ablation_8c7ae1/`

## Order preservation contract

Today `make_batches` sorts by `int(task.source_row_id)` before slicing. That destroys shuffle order.

Required fix (default must match current main-run behavior):

- Add `preserve_input_order: bool = False` to `make_batches(tasks, batch_size, *, preserve_input_order=False)`.
- When `False`, sort by `int(task.source_row_id)` (unchanged).
- When `True`, use `tasks` list order without sorting.
- Thread the same flag through `run_pass(..., preserve_input_order: bool = False)` into `_pending_batches`.

Add a unit-style check (no live API):

```python
def _batch_source_row_ids(batches: list[list[PostTask]]) -> list[str]:
    return [t.source_row_id for batch in batches for t in batch]
```

After the fix, shuffled tasks with `preserve_input_order=True` must not equal sorted row-id order unless the shuffle happened to be sorted.

## Contracts

`ablation_full_dataset/scripts/run_batch_size.py`:

- CLI: `--batch-size` with choices `ABLATION_BATCH_SIZES`.
- Loads tasks via `shuffled_tasks()` (full 26k).
- Calls `run_pass(..., preserve_input_order=True)`.
- Imports and calls post-processing from parent `scripts/run_batch_size.py` (for example `write_parquet_outputs`, `_build_pass_results`, `_write_results_json`, `_write_score_histogram`, `_write_results_markdown`).
- Output dir: `ablation_full_dataset/outputs/batch_{size}/`.

`ablation_full_dataset/scripts/smoke.py`:

- Takes no arguments.
- Loads `shuffled_tasks()`, keeps first 80 tasks in shuffle order (not sorted by row id).
- Deletes prior `ablation_full_dataset/outputs/smoke/batch_60/` and `batch_80/` before running.
- Calls `run_pass` with `preserve_input_order=True`.
- Prints one row per batch size: `batch_size`, `answered`, `deadletter`, `requests`, `p50_request_ms`, `input_tokens`, `estimated_cost_usd`.
- Exits 1 when any batch size has fewer than 80 answered posts.

Main `scripts/run_batch_size.py` changes:

- Extract post-processing into importable functions without changing default CLI behavior.
- After edits, regenerating main-run outputs must be byte-identical to committed files (verify with `git diff outputs/batch_10/` if needed).

## Must pass

Order check (no API):

```bash
cd /workspace/experiments/speedup_jev_2026_09_23 && uv run python -c "
from shared.full_dataset import shuffled_tasks
from shared.batch_runner import make_batches
tasks = shuffled_tasks()[:200]
sorted_ids = [t.source_row_id for t in sorted(tasks, key=lambda t: int(t.source_row_id))]
preserved = [t.source_row_id for batch in make_batches(tasks, 20, preserve_input_order=True) for t in batch]
assert preserved != sorted_ids
assert preserved == [t.source_row_id for t in tasks]
print('order_ok')
"
```

Expected output: `order_ok`

Smoke (live API):

```bash
cd /workspace/experiments/speedup_jev_2026_09_23 && uv run python ablation_full_dataset/scripts/smoke.py
```

Expected: two rows with `answered=80`, `deadletter=0`, exit code 0. Batch size 60 has `requests=2` (80/60 rounded up). Batch size 80 has `requests=1`.

Main-run regression (no API if outputs already exist):

```bash
cd /workspace/experiments/speedup_jev_2026_09_23 && git diff --stat outputs/batch_10/
```

Expected: no diff after any `run_batch_size.py` refactor unless outputs are regenerated and match committed bytes.

## Must fail

```bash
cd /workspace/experiments/speedup_jev_2026_09_23 && uv run python ablation_full_dataset/scripts/run_batch_size.py --batch-size 1
```

Expected: argparse error (1 is not in `ABLATION_BATCH_SIZES`).

## Done when

1. Shuffled task order survives `make_batches` when `preserve_input_order=True`.
2. Main-run default behavior is unchanged (`preserve_input_order=False`).
3. Smoke passes at batch sizes 60 and 80 with 80/80 posts answered.
4. Ablation `run_batch_size.py` can run one pass and write per-batch RESULTS using imported helpers.
