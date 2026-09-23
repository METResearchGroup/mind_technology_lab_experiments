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

The first pass never ran Qwen. `--backend hf` probed the Hugging Face Inference Router, then **silently fell back to a mock policy**. That was a pipeline choice, not a model failure. The hosted Qwen path is blocked in this environment for three independent reasons:

1. **No GPU on the agent VM.** `nvidia-smi` is missing. Full `Qwen/Qwen3.5-4B` BF16 weights are ~9.3 GB, which does not fit cleanly in the ~10 GB of free RAM next to other processes.
2. **The only live Inference Provider for `Qwen/Qwen3.5-4B` is Featherless**, and Featherless sits behind Cloudflare. Calls to `Qwen/Qwen3.5-4B:featherless-ai` return HTTP 403 / Cloudflare error 1010 (browser-integrity / bot block) from `api.featherless.ai`. Other router ids return `model_not_supported`. Together also 403s from this IP. This is not an invalid `HF_TOKEN`.
3. **Hugging Face Jobs cannot start.** `POST /api/jobs/mtorres98` returns HTTP 402: prepaid credit balance is insufficient. `canPay` is false on the token’s account. Jobs are pay-as-you-go; they are not free just because the VM has an `HF_TOKEN`.

`--backend hf` now tries the router first, then downloads `unsloth/Qwen3.5-4B-GGUF` (`Q4_K_M`) from the Hub and serves it with `llama-server`. It does **not** fall back to mock unless you pass `--allow-mock-fallback`.

This workspace's live run used that Hub GGUF path (`backend=hf-local`, `Qwen/Qwen3.5-4B`). On the 8-item seed set:

- IRP resistance 100 → 83.3 from base to profile-only (−16.7)
- Useful-item recall 20 → 10 (−10)
- Sycophancy resistance 75 → 25 (−50)

Those are heuristic-judge scores on a tiny set, not the paper's 13-model Table 2. Retrieval-only IRP stayed at 100 because the factual queries still do not route to memory.

Recompute:

```bash
# from the repository root
uv sync --all-packages --extra test

# mock (CI / no weights)
PYTHONPATH=autoresearch/hidden_costs_of_personalization_2026_09_09 \
  uv run python autoresearch/hidden_costs_of_personalization_2026_09_09/scripts/run_replication.py \
  --backend mock

# Qwen via Hugging Face: router if reachable, otherwise Hub GGUF + llama-server
PYTHONPATH=autoresearch/hidden_costs_of_personalization_2026_09_09 \
  uv run python autoresearch/hidden_costs_of_personalization_2026_09_09/scripts/run_replication.py \
  --backend hf --hf-local
```

`llama-server` must be on `PATH` or at `/tmp/llama.cpp/build/bin/llama-server` (or set `LLAMA_SERVER_BIN`). The Hub download uses `HF_TOKEN` when present.

The same command also writes `dashboard/data/replication.json` for the Next.js dashboard in `dashboard/`. From that folder: `npm install && npm run dev`.

A claimable Vercel preview is created with:

```bash
cd autoresearch/hidden_costs_of_personalization_2026_09_09/dashboard
npx vercel deploy --temporary -y
```

If you import this GitHub repo into Vercel, set the root directory to `autoresearch/hidden_costs_of_personalization_2026_09_09/dashboard`.

Tests: `uv run pytest tests/test_prisk_replication.py`.

Original code and data: https://github.com/yumeng-10/personalization_risk
