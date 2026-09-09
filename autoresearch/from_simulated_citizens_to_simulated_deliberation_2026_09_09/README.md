# From simulated citizens to simulated deliberation

Replication of [Jang et al., arXiv:2609.07573](https://arxiv.org/abs/2609.07573), requested on 2026-09-09.

The paper asks whether LLM persona agents can stand in for a public in two ways:

1. Opinion representation. Do census-balanced Korean personas reproduce national survey splits on eight environmental and low-birthrate policy questions?
2. Interaction. Does stance movement in a six-person, three-round debate depend on hearing other agents?

The paper's answer is no on both counts, at least with GPT-4.1-mini. Persona answers are far more concentrated than the surveys, and they often reverse which demographic group is more supportive. Sealed-monologue rooms, where agents never see one another, still end near the same final split. Restating an assigned side in round 1 almost stops updating.

This folder repeats a scaled version of that pipeline. It uses 160 jointly balanced personas (one per sex x age x education x region cell) instead of 640. Personas are real draws from nvidia/Nemotron-Personas-Korea. The full survey and debate rows in `results/` come from a dummy client calibrated to the paper's GPT-4.1-mini overall A-shares. A 36-row live Qwen3.5-4B sample sits beside those numbers. If the Nemotron download fails, the sampler can fill the same cells with synthetic profiles. `--dummy` writes the calibrated JSON without calling a model.

## What this run does

- Forced-choice survey in Korean, option order randomized, temperature 0.
- Group A-shares compared with KEI and PCASPP benchmarks transcribed from Appendix A.
- Six-agent rooms on climate technology and education-care, plus housing and environmental priority in the full setting.
- Protocols: open debate, sealed monologue, all-A, all-B, and side restated.
- A Next.js dashboard that shows the paper's tables, this run's numbers, and one room's transcript.

It does not rerun the US Pew pool, the original questionnaire scoring in Appendix C, or GPT-4.1 discourse-quality judging.

## How to run

From the repository root:

```bash
uv sync --all-packages --extra test
export HF_TOKEN=...
uv run python autoresearch/from_simulated_citizens_to_simulated_deliberation_2026_09_09/run_experiment.py --mini
```

Useful flags:

- `--mini` uses one debate replica and, for a live model, a 40-persona survey slice.
- `--dummy` skips the model and writes paper-calibrated choices.
- `--no-synthetic` fails if Nemotron-Personas-Korea cannot fill every cell.

Outputs land in `results/` and are copied to `dashboard/public/data/dashboard.json`.

```bash
cd autoresearch/from_simulated_citizens_to_simulated_deliberation_2026_09_09/dashboard
npm install
npm run dev
```

## Tests

```bash
uv run pytest autoresearch/from_simulated_citizens_to_simulated_deliberation_2026_09_09/tests -q
```
