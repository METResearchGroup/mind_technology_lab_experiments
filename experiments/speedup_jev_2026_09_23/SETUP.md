# Setup

This experiment is standalone. Install from this folder, not from the repository root.

```bash
cd experiments/speedup_jev_2026_09_23 && uv sync
```

The command creates a local `.venv` for this experiment, and it does not change the root workspace lock.

## Sample

- URI: `s3://mind-technology-lab-experiments/experiments/moral_outrage_classification_2026_09_19/data/sample_1000.parquet`
- Manifest: `data/sample_1000.manifest.json` (downloaded with the sample)
- Seed: `20260919`, 1,000 rows, 560 gold 0 / 440 gold 1

## Region

The region is hardcoded as `us-east-2` for Secrets Manager, sample download, and artifact upload.

## Secrets

- Secret `jev-typesafe-api-key`, JSON field `TYPESAFE_API_KEY`

## AWS keys

Prefer `LAB_AWS_ACCESS_KEY_ID` and `LAB_AWS_ACCESS_KEY_SECRET` when both are set. Otherwise use `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`. If `AWS_SECRET_ACCESS_KEY` is empty, use `AWS_ACCESS_KEY_SECRET`.

## Model

- Pinned model: `jev-1.13.0`

## Batch sizes

Run batch sizes 1, 5, 10, 20, 30, and 40 posts per request.

## Concurrency

- 8 worker threads per pass
- Cap request starts at 1,000 per minute across all threads

## Jev price

$0.042 per 1 million input tokens and $0 per 1 million output tokens, from [TypeSafe models](https://docs.typesafe.ai/models) as read on 2026-09-23.

## Output prefix

`s3://mind-technology-lab-experiments/experiments/speedup_jev_2026_09_23/`

## Run order

```bash
uv run python scripts/fetch_inputs.py
uv run python scripts/check_typesafe_key.py
uv run python scripts/smoke.py
uv run python scripts/run_batch_size.py --batch-size N
uv run python scripts/write_results.py
uv run python scripts/upload_s3.py
```

Replace `N` with each batch size: 1, 5, 10, 20, 30, and 40.
