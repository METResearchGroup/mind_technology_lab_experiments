# Setup

This experiment is standalone. Install from this folder, not from the repository root.

```bash
cd experiments/moral_outrage_classification_2026_09_19 && uv sync
```

The command creates a local `.venv` for this experiment, and it does not change the root workspace lock.

## Dataset

- URI: `s3://met-research-group-datasets/moral_outrage_classifier/26k_training_data.csv`
- Text column: `text`
- Gold label column: `outrage` (stored as int 0 or 1)
- Row id: original CSV data-row index, stored as `source_row_id`
- Sample: 1,000 rows, 560 gold 0 / 440 gold 1, seed `20260919`
- Sample path: `data/sample_1000.parquet`
- Manifest path: `data/sample_1000.manifest.json`
- Stored Perspective labels: `s3://met-research-group-datasets/moral_outrage_classifier/perspective_api_labeled_26k_twitter_dataset.csv`
- Local Perspective labels path: `data/perspective_api_labeled_26k_twitter_dataset.csv`
- Perspective score column: `pred_label` (`0.0`, `1.0`, or empty). Join the sample by `source_row_id`. Empty labels drop at comparison.

## Region

The region is hardcoded as `us-east-2` for Secrets Manager, Bedrock, dataset download, and artifact upload.

## Secrets

- Secret `jev-typesafe-api-key`, JSON field `TYPESAFE_API_KEY`
- Secret `google-api-key`, JSON field `GOOGLE_API_KEY`. Perspective scoring does not use this key. The scorer reads the stored labels file.

## AWS keys

Prefer `LAB_AWS_ACCESS_KEY_ID` and `LAB_AWS_ACCESS_KEY_SECRET` when both are set. Otherwise use `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`. If `AWS_SECRET_ACCESS_KEY` is empty, use `AWS_ACCESS_KEY_SECRET`.

## Bedrock model IDs

- `us.openai.gpt-5.6-luna`
- `us.openai.gpt-5.6-terra`
- `us.anthropic.claude-sonnet-5`
- `qwen.qwen3-32b-v1:0`
- `deepseek.v3-v1:0`

## Output prefix

`s3://mind-technology-lab-experiments/experiments/moral_outrage_classification_2026_09_19/`

## Bedrock prices

These are hardcoded USD prices per 1 million tokens, copied on 2026-09-19 from [Amazon Bedrock Pricing](https://aws.amazon.com/bedrock/pricing/) and from the us-east-2 on-demand listings for model IDs that the static price tables do not expand:

- `us.openai.gpt-5.6-luna`: $0.22 input / $1.32 output
- `us.openai.gpt-5.6-terra`: $2.20 input / $13.20 output
- `us.anthropic.claude-sonnet-5`: $3.00 input / $15.00 output
- `qwen.qwen3-32b-v1:0`: $0.15 input / $0.60 output
- `deepseek.v3-v1:0`: $0.58 input / $1.68 output

TypeSafe Jev has no public token price, so smoke reports its cost as `unknown`. Perspective is $0.
