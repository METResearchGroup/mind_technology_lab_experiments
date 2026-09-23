# Step 3: Run the five full passes

Score all 26,000 shuffled posts at batch sizes 10, 20, 40, 60, and 80, one pass after another. Each pass writes outputs under `ablation_full_dataset/outputs/batch_{size}/`.

## Files to inspect

- `/workspace/experiments/speedup_jev_2026_09_23/ablation_full_dataset/scripts/run_batch_size.py` (from step 2)
- `/workspace/experiments/speedup_jev_2026_09_23/shared/rate_limiter.py` (`MAX_REQUEST_STARTS_PER_MINUTE = 1000`)
- `/workspace/experiments/speedup_jev_2026_09_23/shared/batch_runner.py` (`WORKER_THREADS = 8`)

## Files allowed to change

- `/workspace/experiments/speedup_jev_2026_09_23/ablation_full_dataset/README.md` (add full-run commands)
- `/workspace/experiments/speedup_jev_2026_09_23/ablation_full_dataset/outputs/batch_*/` (generated)

## Files forbidden to change

- `/workspace/experiments/speedup_jev_2026_09_23/shared/batch_runner.py` unless step 2 left a bug
- Main-run outputs under `/workspace/experiments/speedup_jev_2026_09_23/outputs/batch_*`
- The plan files under `/workspace/docs/plans/2026-09-23_speedup-jev-full-dataset-ablation_8c7ae1/`

## Pass schedule

Run in this order (sequential, not parallel):

| batch size | requests | notes |
| ---: | ---: | --- |
| 10 | 2600 | rate cap binds (~2.6 min floor) |
| 20 | 1300 | |
| 40 | 650 | |
| 60 | 434 | last request has 20 posts |
| 80 | 325 | last request has 40 posts |

Total requests about 5,309. Estimated API wall time about 10 minutes with cap.

Command per pass:

```bash
cd /workspace/experiments/speedup_jev_2026_09_23 && uv run python ablation_full_dataset/scripts/run_batch_size.py --batch-size <N>
```

Each pass must write under `ablation_full_dataset/outputs/batch_<N>/`:

- `predictions.jsonl`, `requests.jsonl`, `runs.jsonl`
- `labels.parquet`, `requests.parquet`
- `results.json`, `RESULTS.md`
- `static/score_hist.png`

Final stdout line per pass (from `run_pass`):

```text
batch_size=<N> scored=26000 deadletter=0 requests=<count>
```

## Must pass

After all five passes:

```bash
cd /workspace/experiments/speedup_jev_2026_09_23 && for n in 10 20 40 60 80; do
  test -s ablation_full_dataset/outputs/batch_${n}/results.json || exit 1
  uv run python -c "import json; r=json.load(open('ablation_full_dataset/outputs/batch_${n}/results.json')); assert r['n_scored']==26000 and r['n_deadletter']==0, r"
done && echo all_passes_ok
```

Expected output: `all_passes_ok`

Spot check batch size 10 rate binding:

```bash
cd /workspace/experiments/speedup_jev_2026_09_23 && uv run python -c "
import json
r = json.load(open('ablation_full_dataset/outputs/batch_10/results.json'))
ppm = r['n_scored'] / r['wall_time_seconds'] * 60
proj = 1000 * 10
print('sustained_ppm', round(ppm, 1), 'projected_ppm', proj, 'wall_s', round(r['wall_time_seconds'], 1))
"
```

Expected: `sustained_ppm` well below `projected_ppm` 10000 (cap binds). `wall_s` at least about 150 (2,600 requests at 1,000/min floor).

```bash
cd /workspace/experiments/speedup_jev_2026_09_23 && git diff --stat outputs/batch_10/
```

Expected: no diff (main run untouched).

## Must fail

Re-running a pass without clearing outputs should not double-score (skip logic in `run_pass`):

```bash
cd /workspace/experiments/speedup_jev_2026_09_23 && uv run python ablation_full_dataset/scripts/run_batch_size.py --batch-size 80 2>&1 | tail -1
```

Expected last line still shows `scored=26000` and does not start 325 new requests from scratch (requests count unchanged in `runs.jsonl` append behavior; wall time for second run near zero).

## Done when

1. All five batch sizes scored 26,000 posts with zero deadletters (or deadletters are documented and investigated).
2. Each `results.json` has F1, latency percentiles, tokens, and cost fields populated.
3. Main-run outputs remain unchanged on disk.
