# LifeMem replication (arXiv:2608.19621)

Replication of [Mitigating Identity Essentialism in LLM Agents with Longitudinal Life Trajectories](https://arxiv.org/abs/2608.19621) (Wang, Zhou, Du, Su, Cao, Pan, Ai, Wu, Zhang, Liu). Official code: [halsayxi/LifeMem](https://github.com/halsayxi/LifeMem).

The paper's claim: static demographic prompts make LLM survey agents essentialist — within-group answers collapse, SES clusters separate. LifeMem stores life events in a hippocampal retriever (top-K=5, α=0.9) and consolidates them into a per-agent LoRA adapter.

## What this folder runs

Add Health and Understanding Society public-use files are restricted. This folder does not ship respondent microdata.

It does ship:

1. The paper's published Table 1–3 and appendix sweeps (Tables 12, 13, 14, 15).
2. A synthetic six-wave panel (24 agents, 8 Likert items, 12 event types) with the same metrics: KL, within-group pairwise gap, entropy gap, transition JS, SES silhouette.
3. Method prompts for Direct, Profile, Anti-stereotype, Full History, Event RAG, Random Event, LifeMem, and the two ablations.
4. A hashed n-gram encoder in place of MiniLM / bge-m3, and a persistent event-binding vector in place of LoRA, so the CPU path stays deterministic.

The default GPU backbone for a full run is `Qwen/Qwen3.5-4B` (lab default). The paper used Llama-3.1-8B-Instruct, Ministral-3-8B-Instruct-2512, and Qwen3.5-9B.

## Run the CPU suite

From the repository root:

```bash
uv sync --all-packages --extra test
uv run pytest autoresearch/mitigating_identity_essentialism_lifemem_2026_09_09/tests -q
uv run python autoresearch/mitigating_identity_essentialism_lifemem_2026_09_09/scripts/export_dashboard_data.py
```

That writes `data/replication_results.json` and `dashboard/public/data/results.json`.

## Dashboard

Live Vercel preview: [https://temporary-prompt-birch-7xdekgc.vercel.app](https://temporary-prompt-birch-7xdekgc.vercel.app)

That URL is an anonymous Vercel deploy. Claim it to keep it: [claim deployment](https://vercel.com/claim-deployment?code=81a2f69e-26b4-4b8c-9839-e6ce949a0df1). A durable static mirror is on Hugging Face: [mtorres98/lifemem-identity-dashboard](https://huggingface.co/spaces/mtorres98/lifemem-identity-dashboard).

```bash
cd autoresearch/mitigating_identity_essentialism_lifemem_2026_09_09/dashboard
npm install
npm run dev
```

The UI has the paper takeaways, Table 1 charts, identity PCA, the synthetic ranking, a compose-a-person control, retrieval scores, latency, and hyperparameter sweeps.

## GPU run (Hugging Face Jobs)

The lab default backbone is `Qwen/Qwen3.5-4B`. `scripts/hf_job.py` loads that model, trains a PEFT LoRA adapter per agent for LifeMem / `lifemem_no_struct`, and scores the same nine methods.

Jobs cannot see this git checkout. `scripts/submit_hf_job.py` uploads `lifemem/` to a Hub dataset, then submits:

```bash
uv run python autoresearch/mitigating_identity_essentialism_lifemem_2026_09_09/scripts/submit_hf_job.py
```

Default hardware is `a10g-small` (24 GB), 8 agents × 6 waves, timeout 8h. The GPU job keeps Table 7 LoRA rank/alpha but trains with batch size 1 and a 768-token cap so Qwen3.5-4B linear-attention backward fits in 24 GB. Results go to `data/gpu_results.json`, Hub dataset `mtorres98/lifemem-replication-2026-09-09`, and `s3://mind-technology-lab-experiments/autoresearch/mitigating_identity_essentialism_lifemem_2026_09_09/`.

Jobs need a credit balance on the submitting namespace. If Jobs returns HTTP 402, `scripts/submit_runpod_job.py` runs the same `scripts/hf_job.py` on a GPU pod.

After a job finishes:

```bash
uv run python autoresearch/mitigating_identity_essentialism_lifemem_2026_09_09/scripts/fetch_gpu_results.py
uv run python autoresearch/mitigating_identity_essentialism_lifemem_2026_09_09/scripts/export_dashboard_data.py
```

Completed Qwen/Qwen3.5-4B run on Hugging Face Jobs (`a10g-small`, NVIDIA A10G, 8 agents × 6 waves): [job](https://huggingface.co/jobs/mtorres98/6aa1b5f15527934177ebdaa5), [gpu_results.json](https://huggingface.co/datasets/mtorres98/lifemem-replication-2026-09-09/blob/main/gpu_results.json).

| Method | KL |
| --- | --- |
| Direct | 14.56 |
| Profile | 9.31 |
| Event RAG | 8.66 |
| LifeMem (no param) | 8.66 |
| Anti-stereotype | 7.84 |
| Full history | 7.69 |
| LifeMem (no struct) | 7.42 |
| Random event | 7.24 |
| LifeMem | 9.21 |

LifeMem is close to Profile on KL. Last-wave SES silhouette falls from 0.39 (Profile) to 0.05 (LifeMem), near the synthetic humans (−0.03). The paper's KL ranking used 8B/9B instruct models.
