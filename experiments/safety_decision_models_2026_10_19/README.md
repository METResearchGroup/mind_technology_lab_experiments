# Safety decision model benchmark

Standalone study comparing typed decision models and Amazon Bedrock Guardrails on public safety and emotion datasets.

## Arms

- `jev` — TypeSafe Jev `jev-1.13.0`
- `clef` — Cloudflare Workers AI `@cf/cloudflare/clef`
- `clef-flash` — Cloudflare Workers AI `@cf/cloudflare/clef-flash`
- `guardrails` — Bedrock `ApplyGuardrail` (detect-only, content filters)

## Datasets (eleven)

ToxiGen, OpenAI Moderation, ToxicChat, prompt injections, WildGuardMix, Do-Not-Answer, XSTest, HarmBench, JailbreakBench, GoEmotions, and Emotion.

## Docs

- [SETUP.md](./SETUP.md) — credentials, install, S3 prefix
- [RESULTS.md](./RESULTS.md) — harness numbers (filled in later steps)

## Plan

Design and steps: `docs/plans/2026-10-19_safety-decision-model-benchmark_a7c3e1/`.
