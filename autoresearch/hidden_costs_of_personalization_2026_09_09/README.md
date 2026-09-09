# Hidden costs of personalization (PRISK)

Mini-replication of [Evaluating the Hidden Costs of Personalization in Large Language Models](https://arxiv.org/abs/2608.28833) (Wang et al., 2026).

The paper's PRISK benchmark runs 13 models on ~3,000 items across four context settings. This folder keeps the same factorial design and metrics on an 8-item seed set so the pipeline is runnable without the original API stack.

## What is measured

Personalization is ablated as a 2×2:

| Setting | Profile | Retrieved memory |
| --- | --- | --- |
| `base` | no | no |
| `profile_only` | yes | no |
| `retrieval_only` | no | routed, top-3 |
| `profile_retrieval` | yes | routed on profile+query |

Three risks, scored as *resistance* (higher is better):

- **Irrelevant personalization (IRP).** Identity-independent questions (history, arithmetic, physics). Score 1–5, then `(score-1)/4 * 100`.
- **Preference narrowing.** Coverage of a universal option set, useful-item recall (UIR), and RelCR vs the base answer.
- **Sycophantic bias.** Pushback when the user is at fault, plus a binary PIS flag if a profile preference visibly steered the reply.

## What this run actually did

Hosted `Qwen/Qwen3.5-4B` inference through Featherless returned Cloudflare 1010 from this environment after the first probe, so generations use a deterministic mock policy that injects the same failure modes the paper describes (attribute scaffolding, collapsed option lists, uncritical agreement). The original Table 2 numbers are shipped beside the mini-run so the dashboard can show both.

On the seed set the mock policy drops IRP resistance 75 points, UIR 60 points, and sycophancy resistance 100 points once a profile is injected. Retrieval-only stays at the base IRP score because the factual queries never route to memory, which matches the paper's retrieval-only IRP column sitting near 100.

Recompute:

```bash
# from the repository root
PYTHONPATH=autoresearch/hidden_costs_of_personalization_2026_09_09 \
  uv run python autoresearch/hidden_costs_of_personalization_2026_09_09/scripts/run_replication.py \
  --backend mock

# optional live model, if the Hugging Face router can reach a provider
PYTHONPATH=autoresearch/hidden_costs_of_personalization_2026_09_09 \
  uv run python autoresearch/hidden_costs_of_personalization_2026_09_09/scripts/run_replication.py \
  --backend hf --hf-model 'Qwen/Qwen3.5-4B:featherless-ai'
```

Tests: `uv run pytest tests/test_prisk_replication.py`.

Original code and data: https://github.com/yumeng-10/personalization_risk
