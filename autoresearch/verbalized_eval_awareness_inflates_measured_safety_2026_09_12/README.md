# Verbalized eval awareness briefing

Folder for a read of [Verbalized Eval Awareness Inflates Measured Safety](https://www.goodfire.com/research/verbalized-eval-awareness-inflates-measured-safety) (Aranguri & Bloom, Goodfire / UK AISI, 2026).

This is not a full replication. It is a briefing plus five cheap PoC experiments. Each experiment is capped at **$2** and uses **Qwen3.5-4B** on public benchmarks.

## Dashboard

Static site in `dashboard/`. Review findings, then pick 1–2 experiments.

## Experiments

Specs live in `experiments/specs.json`. Do not run them until a subset is chosen.

| ID | Reviews | Rough API cost |
| --- | --- | --- |
| E1 | Prevalence on StereoSet, BBQ, AIR-Bench | ~$0.18 |
| E2 | Within-item VEA vs safer answers | ~$0.32 |
| E3 | CoT prefill: safety test vs helpfulness test | ~$0.28 |
| E4 | Strip authority wrappers | ~$0.22 |
| E5 | MCQ vs open-ended, 0.8B vs 4B | ~$0.40 |

Pricing assumes Hugging Face Inference Providers or DeepInfra, not a reserved GPU.

## Sources

- Paper: https://www.goodfire.com/research/verbalized-eval-awareness-inflates-measured-safety
- Instance browser: https://aranguri.github.io/eval_awareness/demo/
- Default model: https://huggingface.co/Qwen/Qwen3.5-4B
