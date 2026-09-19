# Setup

Standalone experiment. Install from this folder, not from the repository root.

```bash
cd experiments/moral_outrage_classification_2026_09_19 && uv sync
```

That creates a local `.venv` for this experiment. It does not change the root workspace lock.

## Dataset

- URI: `s3://met-research-group-datasets/moral_outrage_classifier/26k_training_data.csv`
- Text column: `text`
- Gold label column: `outrage` (stored as int 0 or 1)
- Row id: original CSV data-row index, stored as `source_row_id`
- Sample: 1,000 rows, 560 gold 0 / 440 gold 1, seed `20260919`
- Sample path: `data/sample_1000.parquet`
- Manifest path: `data/sample_1000.manifest.json`

## Region

Hardcoded constant `us-east-2` for Secrets Manager, Bedrock, dataset download, and artifact upload.

## Secrets

- Secret `jev-typesafe-api-key`, JSON field `TYPESAFE_API_KEY`
- Secret `google-api-key`, JSON field `GOOGLE_API_KEY`

## AWS keys

Prefer `LAB_AWS_ACCESS_KEY_ID` and `LAB_AWS_ACCESS_KEY_SECRET`. If those names are empty, use `AWS_ACCESS_KEY_ID` and map `AWS_ACCESS_KEY_SECRET` to `AWS_SECRET_ACCESS_KEY`.

## Bedrock model IDs

- `us.openai.gpt-5.6-luna`
- `us.openai.gpt-5.6-terra`
- `us.anthropic.claude-sonnet-5`
- `qwen.qwen3-32b-v1:0`
- `deepseek.v3-v1:0`

## Output prefix

`s3://mind-technology-lab-experiments/experiments/moral_outrage_classification_2026_09_19/`

## Bedrock prices

Hardcoded USD per 1 million tokens, copied 2026-09-19 from [Amazon Bedrock Pricing](https://aws.amazon.com/bedrock/pricing/) and the us-east-2 on-demand listings for IDs the static tables do not expand:

- `us.openai.gpt-5.6-luna`: $0.22 input / $1.32 output
- `us.openai.gpt-5.6-terra`: $2.20 input / $13.20 output
- `us.anthropic.claude-sonnet-5`: $3.00 input / $15.00 output
- `qwen.qwen3-32b-v1:0`: $0.15 input / $0.60 output
- `deepseek.v3-v1:0`: $0.58 input / $1.68 output

TypeSafe Jev has no public token price. Smoke reports its cost as `unknown`. Perspective is $0.
