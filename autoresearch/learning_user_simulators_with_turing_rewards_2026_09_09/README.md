# Learning User Simulators with Turing Rewards (mini replica)

OpenReview: [Learning User Simulators with Turing Rewards](https://openreview.net/forum?id=08Z5or1Jys)
([PDF](https://openreview.net/attachment?id=08Z5or1Jys&name=pdf),
[arXiv:2606.19336](https://arxiv.org/abs/2606.19336)).

This folder is a **bare-minimum replica**. The paper trains Qwen3-8B with LoRA GRPO
and a Qwen3.5-397B Turing judge (about 1680 GPU hours). This environment has no GPU,
so we keep the paper formulas and run a tiny tabular GRPO loop on dummy users.

## Method (paper)

1. SFT warm start on each user's history.
2. GRPO with group size 8. Reward is a pairwise LLM Turing test (Likert 1–7).
3. Mapping: \(r = (\min(s,5)-1)/6\), plus a domain length penalty.
4. Baselines: Sim-RL (content overlap) and Logprob-RL (log \(p(\text{human reply})\)).

Paper result: Turing-RL wins more Turing tests against real users than Sim-RL or
Logprob-RL. Logprob-RL often collapses to short replies.

## What this replica runs

```bash
# from the repository root
uv run python autoresearch/learning_user_simulators_with_turing_rewards_2026_09_09/turing_rl/train.py
uv run pytest tests/test_turing_rl.py
```

Dummy users (Maya, Jordan, Priya) each have a catalog of replies. A heuristic
judge scores replies. GRPO then updates a softmax policy. Turing-RL stays on
human-like replies. Logprob-RL on Reddit collapses to `too_short`.

## Qwen3-8B Hugging Face Job

The paper policy is `Qwen/Qwen3-8B` with thinking off. Full training is about
1680 GPU hours on B200/B300 with a Qwen3.5-397B OpenRouter judge. This folder
submits a **scaled** LoRA SFT + GRPO slice to Hugging Face Jobs (`a100-large`,
3 hour timeout).

```bash
# from the repository root; needs HF_TOKEN
uv run --with huggingface_hub python \
  autoresearch/learning_user_simulators_with_turing_rewards_2026_09_09/jobs/launch_hf_job.py
```

The job script is `jobs/train_qwen3_8b_turing_rl.py` (PEP 723 UV). It pushes
adapters to the Hub and writes metrics JSON under `results/`.

`OPENROUTER_API_KEY` is not in this environment, so the pairwise Turing judge
is `gpt-4o-mini` via `OPENAI_API_KEY`. That is a substitution, not the paper
judge.

## Dashboard

Next.js app in `dashboard/`. It shows paper tables, replica charts, the
Qwen3-8B job, and a live Turing-score playground with an in-browser GRPO
trainer.

```bash
cd dashboard
npm install
npm run dev
```
