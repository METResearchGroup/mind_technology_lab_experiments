# Full 26k Jev batching ablation

This is a separate ablation from the main 1,000-post experiment in the parent folder. It scores all 26,000 posts from the Brady moral outrage training CSV at batch sizes 10, 20, 40, 60, and 80.

Posts are shuffled once with seed `20260923` before batching so every batch size sees the same random order. The model is `jev-1.13.0`.

## Setup

Follow [SETUP.md](../SETUP.md) in the parent experiment for `uv` install and AWS/TypeSafe secrets.

## Commands

Download and validate the full CSV:

```bash
uv run python ablation_full_dataset/scripts/fetch_full_dataset.py
```

Smoke test the first 80 shuffled posts at batch sizes 60 and 80 (live API; about 160 posts total):

```bash
uv run python ablation_full_dataset/scripts/smoke.py
```

Run one full pass for a batch size:

```bash
uv run python ablation_full_dataset/scripts/run_batch_size.py --batch-size 20
```

Results land in `ablation_full_dataset/RESULTS.md` and `ablation_full_dataset/outputs/batch_{size}/`.
