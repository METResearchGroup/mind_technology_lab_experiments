# Setup

## Region

Use **us-east-2** for AWS Secrets Manager and for Bedrock Guardrails calls.

## Install

```bash
cd experiments/safety_decision_models_2026_10_19 && uv sync
```

This experiment is **not** a root uv workspace member. Run `uv sync` in this folder and use the local `.venv` that command creates.

## Secrets (AWS Secrets Manager or environment)

| Secret | Field / use |
| --- | --- |
| `jev-typesafe-api-key` | JSON `TYPESAFE_API_KEY` |
| `hf-token` | Hugging Face token (plain string or JSON token field) for gated datasets |
| `cloudflare-workers-ai` | JSON `account_id`, `api_token` |
| Lab AWS | `LAB_AWS_ACCESS_KEY_ID`, `LAB_AWS_ACCESS_KEY_SECRET` (or standard `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`) |

Never commit secret values.

## S3 output prefix

`s3://mind-technology-lab-experiments/experiments/safety_decision_models_2026_10_19/`

## Do-Not-Answer

Question text from `LibrAI/do-not-answer` is written only to gitignored `data/snapshots/` and `data/records/`. Do not commit that text to git or upload it to S3.
