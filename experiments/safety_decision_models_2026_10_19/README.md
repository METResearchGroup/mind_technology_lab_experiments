# Safety decision model benchmark

This folder holds a standalone benchmark that compares typed decision models and Amazon Bedrock Guardrails on public safety and emotion datasets.

## Arms

- `jev`, TypeSafe Jev `jev-1.13.0`
- `clef`, Cloudflare Workers AI `@cf/cloudflare/clef`
- `clef-flash`, Cloudflare Workers AI `@cf/cloudflare/clef-flash`
- `guardrails`, Bedrock `ApplyGuardrail` in detect-only mode with content filters

## Datasets

The benchmark pulls eleven public datasets: ToxiGen, OpenAI Moderation, ToxicChat, prompt injections, WildGuardMix, Do-Not-Answer, XSTest, HarmBench, JailbreakBench, GoEmotions, and Emotion.

## Docs

- [SETUP.md](./SETUP.md), credentials, install, and S3 prefix
- [RESULTS.md](./RESULTS.md), harness check, core-pack metrics, and logged spend. For JailbreakBench, the core-pack guardrail headline stays on the pre-registered Prompt Attack crosswalk. **Post-hoc sensitivity analysis** in RESULTS.md reports an any-filter variant computed from cached assessments only.

## Plan

Design and steps live in `docs/plans/2026-10-19_safety-decision-model-benchmark_a7c3e1/`.
